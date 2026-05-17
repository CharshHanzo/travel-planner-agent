from typing import Optional, Dict, Any, List
from sqlmodel import Session, select, func
from collections import Counter
import statistics
from app.models.trip import Trip
from app.models.preference import LearnedPreference
import logging

logger = logging.getLogger(__name__)

class LearningEngine:
    """用户偏好学习引擎"""
    
    # 偏好类型定义
    PREFERENCE_TYPES = {
        "taste": "口味偏好",
        "budget": "预算范围",
        "departure": "常用出发地",
        "people_count": "出行人数",
        "activity_count": "活动数量",
    }
    
    # 最低评分阈值（评分 ≤ 2 的行程不计入学习）
    MIN_RATING = 2.0
    
    # 最少样本数（低于此数量认为置信度不足）
    MIN_SAMPLES = 2
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_valid_trips(self, user_id: str) -> List[Trip]:
        """获取用户的有效历史行程（未删除、评分 > 2 或无评分）"""
        query = select(Trip).where(
            Trip.user_id == user_id,
            Trip.is_deleted == False,
            (Trip.rating > self.MIN_RATING) | (Trip.rating == None),
        ).order_by(Trip.created_at.desc())
        return self.session.exec(query).all()
    
    def calculate_preferences(self, user_id: str) -> Dict[str, Any]:
        """计算用户所有偏好"""
        trips = self.get_valid_trips(user_id)
        total = len(trips)
        
        if total < self.MIN_SAMPLES:
            logger.info(f"用户 {user_id} 有效行程数 {total} < {self.MIN_SAMPLES}，不计算偏好")
            return {
                "preferences": {},
                "total_trips": total,
                "sufficient": False,
            }
        
        preferences = {}
        
        # 1. 口味偏好（众数）
        taste_values = [t.taste for t in trips if t.taste and t.taste != "不挑"]
        if taste_values:
            taste_counter = Counter(taste_values)
            most_common = taste_counter.most_common(1)[0]
            preferences["taste"] = {
                "value": most_common[0],
                "confidence": round(most_common[1] / len(taste_values) * 100, 1),
            }
        
        # 2. 预算（中位数）
        budget_values = [t.budget for t in trips if t.budget and t.budget > 0]
        if budget_values:
            median_budget = statistics.median(budget_values)
            preferences["budget"] = {
                "value": int(median_budget),
                "confidence": round(len(budget_values) / total * 100, 1),
            }
        
        # 3. 出发地（众数）
        departure_values = [t.departure for t in trips if t.departure]
        if departure_values:
            dep_counter = Counter(departure_values)
            most_common = dep_counter.most_common(1)[0]
            preferences["departure"] = {
                "value": most_common[0],
                "confidence": round(most_common[1] / len(departure_values) * 100, 1),
            }
        
        # 4. 人数（中位数取整）
        people_values = [t.people_count for t in trips if t.people_count and t.people_count > 0]
        if people_values:
            median_people = statistics.median(people_values)
            preferences["people_count"] = {
                "value": int(round(median_people)),
                "confidence": round(len(people_values) / total * 100, 1),
            }
        
        # 5. 活动数量（中位数取整）
        activity_values = [t.activity_count for t in trips if t.activity_count and t.activity_count > 0]
        if activity_values:
            median_activity = statistics.median(activity_values)
            preferences["activity_count"] = {
                "value": int(round(median_activity)),
                "confidence": round(len(activity_values) / total * 100, 1),
            }
        
        return {
            "preferences": preferences,
            "total_trips": total,
            "sufficient": True,
        }
    
    def save_to_cache(self, user_id: str, preferences_result: Dict[str, Any]):
        """将计算结果缓存到 learned_preferences 表"""
        if not preferences_result.get("sufficient"):
            return
        
        prefs = preferences_result.get("preferences", {})
        import json
        
        for pref_type, pref_data in prefs.items():
            # UPSERT：查找是否存在
            existing = self.session.exec(
                select(LearnedPreference).where(
                    LearnedPreference.user_id == user_id,
                    LearnedPreference.preference_type == pref_type,
                )
            ).first()
            
            if existing:
                existing.value = json.dumps(pref_data, ensure_ascii=False)
                existing.confidence = pref_data["confidence"] / 100
            else:
                new_pref = LearnedPreference(
                    user_id=user_id,
                    preference_type=pref_type,
                    value=json.dumps(pref_data, ensure_ascii=False),
                    confidence=pref_data["confidence"] / 100,
                    source_trips=json.dumps([], ensure_ascii=False),
                )
                self.session.add(new_pref)
        
        self.session.commit()
    
    def update_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """完整的学习流程：计算 → 缓存 → 返回"""
        result = self.calculate_preferences(user_id)
        self.save_to_cache(user_id, result)
        logger.info(f"用户 {user_id} 偏好已更新: {result}")
        return result
    
    def get_cached_preferences(self, user_id: str) -> Dict[str, Any]:
        """从缓存表读取偏好"""
        cached = self.session.exec(
            select(LearnedPreference).where(
                LearnedPreference.user_id == user_id,
            )
        ).all()
        
        if not cached:
            return {
                "preferences": {},
                "total_trips": 0,
                "sufficient": False,
            }
        
        import json
        preferences = {}
        for c in cached:
            try:
                preferences[c.preference_type] = json.loads(c.value)
            except:
                preferences[c.preference_type] = {"value": c.value, "confidence": c.confidence * 100}
        
        return {
            "preferences": preferences,
            "total_trips": 0,  # 缓存不存总数
            "sufficient": True,
        }