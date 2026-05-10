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
            # 支持两种格式：
            # 1. segments 格式（多个路段）
            # 2. 单一路线格式（直接有 path）
            segments_data = route.get("segments", [])
            
            # 如果没有 segments，但有 path，视为单段路线
            if not segments_data and route.get("path"):
                segments_data = [route]
            
            all_segments = []
            for seg in segments_data:
                path = []
                raw_path = seg.get("path", [])
                
                for p in raw_path:
                    if isinstance(p, str) and "," in p:
                        lng, lat = p.split(",")
                        path.append([float(lng.strip()), float(lat.strip())])
                    elif isinstance(p, list) and len(p) == 2:
                        path.append([float(p[0]), float(p[1])])
                    elif isinstance(p, str) and ";" in p:
                        # 处理 polyline 格式："lng1,lat1;lng2,lat2;..."
                        points = p.split(";")
                        for point in points:
                            if "," in point:
                                lng2, lat2 = point.split(",")
                                path.append([float(lng2.strip()), float(lat2.strip())])
                
                if path and len(path) >= 2:
                    all_segments.append({
                        "from": seg.get("from", "起点"),
                        "to": seg.get("to", "终点"),
                        "path": path,
                        "distance": seg.get("distance", ""),
                        "duration": seg.get("duration", ""),
                    })
            
            if all_segments:
                result["route"] = {"segments": all_segments}
        except (ValueError, AttributeError):
            result["route"] = None
    
    # 注意：不再自动生成简单路线
    # 让前端根据实际情况选择使用 AMap.DrivingRoute 或直线连线
    # 如果没有真实路线数据（来自 MCP plan_route），route 保持为 None

    return result
