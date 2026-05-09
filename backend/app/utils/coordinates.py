import re
import json
from typing import Optional, Dict, Any


def extract_coordinates(text: str) -> Optional[Dict[str, Any]]:
    """从文本中提取坐标 JSON 块"""
    if not text:
        return None
    
    # 先恢复正常换行符（处理 AIMessage 字符串化后的转义）
    clean_text = text.replace('\\n', '\n').replace('\\"', '"')
    
    # 匹配 JSON 块（标准格式）
    pattern = r'```json\s*\n(.*?)\n```'
    matches = re.findall(pattern, clean_text, re.DOTALL)
    
    # 如果没找到，尝试更宽松的匹配（可能没有换行）
    if not matches:
        pattern = r'```json\s*(.*?)```'
        matches = re.findall(pattern, clean_text, re.DOTALL)
    
    for match in reversed(matches):
        try:
            data = json.loads(match.strip())
            if 'coordinates' in data:
                return data['coordinates']
            if 'activities' in data or 'restaurants' in data:
                return data
        except json.JSONDecodeError:
            # 尝试修复常见的 JSON 问题
            try:
                fixed = match.strip()
                # 修复 trailing comma 问题
                fixed = re.sub(r',\s*}', '}', fixed)
                fixed = re.sub(r',\s*]', ']', fixed)
                # 修复可能的转义问题
                fixed = fixed.replace('\\"', '"')
                data = json.loads(fixed)
                if 'coordinates' in data:
                    return data['coordinates']
                if 'activities' in data or 'restaurants' in data:
                    return data
            except:
                continue
    
    return None


def remove_coordinates_json(markdown: str) -> str:
    """移除 Markdown 末尾的坐标 JSON 块"""
    if not markdown:
        return markdown
    
    # 移除末尾的 ```json ... ``` 块（支持多种格式）
    cleaned = re.sub(r'\n*```json\s*\n\{[\s\S]*?\n```\s*$', '', markdown)
    
    # 如果没匹配到，尝试更宽松的模式
    if cleaned == markdown:
        cleaned = re.sub(r'\n*```json\s*\{[\s\S]*?```\s*$', '', markdown)
    
    return cleaned.strip()


def format_coordinates_for_frontend(coords: Dict[str, Any]) -> Dict[str, Any]:
    """将坐标数据转换为前端友好格式"""
    result = {
        "points": [],
        "route": None,
    }
    
    # 处理景点
    for activity in coords.get("activities", []):
        try:
            if "location" in activity and activity["location"]:
                parts = activity["location"].split(",")
                if len(parts) == 2:
                    result["points"].append({
                        "name": activity.get("name", "景点"),
                        "lng": float(parts[0].strip()),
                        "lat": float(parts[1].strip()),
                        "type": "activity",
                        "description": activity.get("description", ""),
                        "duration": activity.get("duration", ""),
                    })
        except (ValueError, AttributeError):
            continue
    
    # 处理餐厅
    for restaurant in coords.get("restaurants", []):
        try:
            if "location" in restaurant and restaurant["location"]:
                parts = restaurant["location"].split(",")
                if len(parts) == 2:
                    result["points"].append({
                        "name": restaurant.get("name", "餐厅"),
                        "lng": float(parts[0].strip()),
                        "lat": float(parts[1].strip()),
                        "type": "restaurant",
                        "cuisine": restaurant.get("cuisine", ""),
                        "price_per_person": restaurant.get("price_per_person", 0),
                        "rating": restaurant.get("rating", 0),
                    })
        except (ValueError, AttributeError):
            continue
    
    # 处理路线
    route = coords.get("route")
    if route:
        try:
            segments = route.get("segments", [])
            if segments and isinstance(segments, list):
                formatted_segments = []
                for seg in segments:
                    path = seg.get("path", [])
                    formatted_path = []
                    for p in path:
                        try:
                            if isinstance(p, list) and len(p) >= 2:
                                formatted_path.append([float(p[0]), float(p[1])])
                            elif isinstance(p, str):
                                coords_str = p.split(",")
                                if len(coords_str) == 2:
                                    formatted_path.append([float(coords_str[0].strip()), float(coords_str[1].strip())])
                        except (ValueError, AttributeError):
                            continue
                    
                    formatted_segments.append({
                        "from": seg.get("from", "起点"),
                        "to": seg.get("to", "终点"),
                        "path": formatted_path,
                        "distance": seg.get("distance", ""),
                        "duration": seg.get("duration", ""),
                    })
                
                if formatted_segments:
                    result["route"] = {"segments": formatted_segments}
        except (ValueError, AttributeError):
            result["route"] = None
    
    return result
