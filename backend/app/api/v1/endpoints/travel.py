from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import logging
from sqlmodel import Session
import json
from typing import Optional

from app.api.v1.schemas.travel import TravelRequest, TravelResponse
from app.services.travel_planner import TravelPlannerService
from app.services.user_service import get_or_create_user
from app.services.trip_service import create_trip
from app.db import get_session, engine as db_engine
from app.utils.coordinates import extract_coordinates, format_coordinates_for_frontend, remove_coordinates_json
from app.services.learning_engine import LearningEngine
from app.models.user import User
from app.core.dependencies import get_current_user

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# 服务实例
planner_service = TravelPlannerService()

@router.post("/plan", response_model=TravelResponse)
async def plan_travel(
    travel_request: TravelRequest,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user),
):
    try:
        logger.error("【DEBUG】plan_travel 被调用")
        
        # 执行规划
        raw_result = await planner_service.plan_travel(travel_request)
        
        # 解析坐标数据（从原始结果中提取）
        coordinates = extract_coordinates(raw_result)
        
        # 清理 Markdown（移除末尾的坐标 JSON 块）
        result_markdown = remove_coordinates_json(raw_result)
        formatted_coords = format_coordinates_for_frontend(coordinates) if coordinates else None
        
        # 保存行程记录
        trip = create_trip(
            session=session,
            user_id=current_user.id if current_user else None,
            device_id=travel_request.device_id if not current_user else None,
            city=travel_request.city,
            travel_date=travel_request.travel_date.isoformat(),
            people_count=travel_request.people_count,
            budget=travel_request.budget,
            taste=travel_request.taste,
            departure=travel_request.departure,
            activity_count=travel_request.activity_count,
            plan_markdown=result_markdown,
            mode="quick",
            coordinates_data=json.dumps(coordinates, ensure_ascii=False) if coordinates else None,
        )
        logger.error(f"【DEBUG】create_trip 完成，trip_id={trip.id}")
        
        # 触发学习更新（用独立 session，不影响主流程）
        try:
            with Session(db_engine) as learning_session:
                engine = LearningEngine(learning_session)
                engine.update_user_preferences(user.id)
        except Exception as e:
            logger.error(f"更新用户偏好失败: {e}")
        
        # 构建响应
        response = TravelResponse(
            session_id=f"session-{datetime.now().timestamp()}",
            status="completed",
            result_markdown=result_markdown,
            created_at=datetime.now(),
            coordinates=formatted_coords,
        )
        
        return response
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"无法连接到 MCP 服务器：{e}")
        raise HTTPException(status_code=503, detail=f"无法连接到 MCP 服务器：{str(e)}")
    except Exception as e:
        logger.error(f"旅行规划执行错误：{e}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误：{str(e)}")