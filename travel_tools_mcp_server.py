import httpx
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv
load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
AMAP_API_KEY = os.getenv("AMAP_API_KEY")  # 新增：高德地图 API Key

# 配置区域
FORECAST_BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
GEOCODING_BASE_URL = "http://api.openweathermap.org/geo/1.0/direct"
FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"
AMAP_BASE_URL = "https://restapi.amap.com/v3"


# API 端点
mcp = FastMCP(
    name="Travel Tools Service",
    host="127.0.0.1",
    port=8000,
    stateless_http=True,
    json_response=True,
)

# 天气工具相关

# 辅助函数
async def get_coordinates(city: str):
    """
    根据城市名称获取经纬度坐标
    """
    async with httpx.AsyncClient() as client:
        params = {
            "q": city,
            "limit": 1,
            "appid": OPENWEATHER_API_KEY
        }
        response = await client.get(GEOCODING_BASE_URL, params=params)
        
        if response.status_code != 200 or not response.json():
            return None, None
        
        data = response.json()[0]
        return data.get("lat"), data.get("lon")

def parse_date(date_str: str) -> str:
    """
    解析用户输入的日期，返回 YYYY-MM-DD 格式
    支持：明天、后天、2026-04-20、4月20日 等
    """
    from datetime import datetime, timedelta
    
    # 处理相对日期
    if date_str == "明天":
        target_date = datetime.now() + timedelta(days=1)
        return target_date.strftime("%Y-%m-%d")
    elif date_str == "后天":
        target_date = datetime.now() + timedelta(days=2)
        return target_date.strftime("%Y-%m-%d")
    elif date_str == "今天":
        return datetime.now().strftime("%Y-%m-%d")
    
    # 尝试解析 YYYY-MM-DD 格式
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        pass
    
    # 如果都不匹配，返回原字符串（后续会报错提示）
    return date_str

async def get_weather_by_date(city: str, target_date: str):
    """
    获取指定日期的天气预报
    """
    # 1. 获取坐标
    lat, lon = await get_coordinates(city)
    if lat is None:
        return {"error": f"未找到城市：{city}"}
    
    # 2. 获取5天预报数据
    async with httpx.AsyncClient() as client:
        params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "zh_cn",
            "cnt": 40  # 5天 * 8个时段 = 40个数据点
        }
        response = await client.get(FORECAST_BASE_URL, params=params)
        
        if response.status_code != 200:
            return {"error": f"API 请求失败：{response.status_code}"}
        
        data = response.json()
        
        # 3. 查找匹配日期的数据
        target_date_str = parse_date(target_date)
        
        # 从预报列表中查找日期匹配的数据
        for forecast in data["list"]:
            forecast_date = forecast["dt_txt"].split(" ")[0]  # 提取 YYYY-MM-DD
            if forecast_date == target_date_str:
                return {
                    "city": city,
                    "date": target_date_str,
                    "temperature": forecast["main"]["temp"],
                    "feels_like": forecast["main"]["feels_like"],
                    "humidity": forecast["main"]["humidity"],
                    "pressure": forecast["main"]["pressure"],
                    "wind_speed": forecast["wind"]["speed"],
                    "weather_desc": forecast["weather"][0]["description"],
                    "rain": forecast.get("rain", {}).get("3h", 0)  # 降雨量
                }
        
        # 没找到精确匹配，返回最近一天的预报
        if data["list"]:
            nearest = data["list"][0]
            return {
                "city": city,
                "date": target_date_str,
                "temperature": nearest["main"]["temp"],
                "feels_like": nearest["main"]["feels_like"],
                "humidity": nearest["main"]["humidity"],
                "pressure": nearest["main"]["pressure"],
                "wind_speed": nearest["wind"]["speed"],
                "weather_desc": nearest["weather"][0]["description"],
                "note": f"（未找到{target_date_str}的预报，显示最近时间）"
            }
        
        return {"error": f"未找到{city}的天气预报数据"}


# Weather Agent 工具函数
@mcp.tool()
async def get_weather(city: str, date: str) -> str:
    """
    获取指定城市在目标日期的天气信息。
    
    Args:
        city: 城市名称，如"广州"、"Beijing"
        date: 日期，支持"今天"、"明天"、"后天"、或具体日期如"2026-04-20"
    
    Returns:
        格式化的天气信息
    """
    print(f"[DEBUG] 查询天气：城市={city}, 日期={date}")
    
    weather_data = await get_weather_by_date(city, date)
    
    if "error" in weather_data:
        return f"{weather_data['error']}"
    
    # 格式化输出
    note = weather_data.get("note", "")
    rain_info = f"\n☔ 降雨量：{weather_data['rain']} mm" if weather_data.get("rain", 0) > 0 else ""
    
    return (
        f"{weather_data['date']}{note}\n"
        f"{weather_data['city']}\n"
        f"温度：{weather_data['temperature']}°C（体感 {weather_data['feels_like']}°C）\n"
        f"湿度：{weather_data['humidity']}%\n"
        f"风速：{weather_data['wind_speed']} m/s\n"
        f"气压：{weather_data['pressure']} hPa\n"
        f"天气：{weather_data['weather_desc']}{rain_info}\n"
    )

# Activity Agent 工具函数
# 辅助函数
async def _geocode(address: str) -> str:
    """地址转坐标，返回 '经度,纬度'"""
    if not AMAP_API_KEY:
        return None
    
    async with httpx.AsyncClient() as client:
        params = {
            "key": AMAP_API_KEY,
            "address": address
        }
        response = await client.get(f"{AMAP_BASE_URL}/geocode/geo", params=params)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        if data.get("status") == "1" and data.get("geocodes"):
            return data["geocodes"][0]["location"]
    
    return None

async def _get_distance(origin: str, dest: str) -> dict:
    """获取两点间的驾车距离（公里）和时间（分钟）"""
    if not AMAP_API_KEY:
        return {"distance_km": 0, "duration_min": 0}
    
    async with httpx.AsyncClient() as client:
        params = {
            "key": AMAP_API_KEY,
            "origins": origin,
            "destination": dest,
            "type": 0  # 0: 驾车距离
        }
        response = await client.get(f"{AMAP_BASE_URL}/distance", params=params)
        
        if response.status_code != 200:
            return {"distance_km": 0, "duration_min": 0}
        
        data = response.json()
        if data.get("status") == "1" and data.get("results"):
            result = data["results"][0]
            distance_m = int(result.get("distance", 0))
            duration_s = int(result.get("duration", 0))
            return {
                "distance_km": round(distance_m / 1000, 1),
                "duration_min": round(duration_s / 60, 1)
            }
    
    return {"distance_km": 0, "duration_min": 0}

@mcp.tool()
async def search_activities(city: str, keyword: str = "景点", limit: int = 10) -> dict:
    """
    搜索目的地的景点、活动、节庆等
    
    Args:
        city: 城市名称，如"杭州"
        keyword: 搜索类型，如"景点"、"演出"、"亲子"、"博物馆"
        limit: 返回数量，默认10
    
    Returns:
        活动列表，每个活动包含名称、描述和位置信息
    """
    if not FIRECRAWL_API_KEY:
        return {"error": "未配置 Firecrawl API Key，请在 .env 文件中设置 FIRECRAWL_API_KEY"}
    
    # 构建搜索查询
    query = f"{city} {keyword} 推荐 攻略"
    
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": query,
            "limit": limit,
            "formats": ["markdown"]
        }
        
        try:
            response = await client.post(
                f"{FIRECRAWL_BASE_URL}/search",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code != 200:
                return {"error": f"搜索失败：{response.status_code}"}
            
            data = response.json()
            
            if not data.get("success"):
                return {"error": data.get("error", "搜索失败")}
            
            results = []
            for item in data.get("data", []):
                metadata = item.get("metadata", {})
                content = item.get("markdown", "")
                
                # 尝试从内容中提取位置信息
                location_hint = None
                for line in content.split("\n")[:20]:  # 只看前20行
                    if "地址" in line or "位置" in line or "位于" in line:
                        location_hint = line.strip()
                        break
                
                results.append({
                    "name": metadata.get("title", "").split(" - ")[0],
                    "description": content[:300] + "..." if len(content) > 300 else content,
                    "location_hint": location_hint,
                    "source_url": metadata.get("sourceURL", "")
                })
            
            return {
                "city": city,
                "keyword": keyword,
                "count": len(results),
                "activities": results
            }
        
        except Exception as e:
            return {"error": f"请求异常：{str(e)}"}

@mcp.tool()
async def plan_route(activities: list, start_point: str = None) -> dict:
    """
    规划多个活动的游览顺序
    
    Args:
        activities: 活动列表，格式 [{"name": "故宫", "location": "北京市东城区景山前街4号"}, ...]
                    location 可以是详细地址或"经度,纬度"坐标
        start_point: 起点坐标（可选），格式"经度,纬度"
    
    Returns:
        优化后的顺序和交通时间
    """
    if len(activities) < 2:
        return {
            "error": "至少需要2个活动才能规划路线",
            "optimized_order": [act.get("name", "未知") for act in activities]
        }
    
    if not AMAP_API_KEY:
        return {
            "error": "未配置高德地图 API Key，无法计算路线",
            "optimized_order": [act.get("name", "未知") for act in activities],
            "note": "仅返回原始顺序，未优化"
        }
    
    # 1. 获取所有坐标
    coords = []
    names = []
    failed = []
    
    for act in activities:
        name = act.get("name", "未知")
        loc = act.get("location", "")
        
        names.append(name)
        
        # 判断是坐标还是地址
        if "," in loc and len(loc.split(",")) == 2:
            # 已经是坐标格式
            coords.append(loc)
        elif loc:
            # 需要地理编码
            coord = await _geocode(f"{loc} {name}")
            if coord:
                coords.append(coord)
            else:
                failed.append(name)
                coords.append(None)
        else:
            failed.append(name)
            coords.append(None)
    
    if failed:
        return {
            "error": f"无法定位以下活动：{', '.join(failed)}",
            "optimized_order": names,
            "note": "请为这些活动提供更详细的位置信息"
        }
    
    # 2. 计算距离矩阵
    n = len(coords)
    dist_matrix = [[0] * n for _ in range(n)]
    time_matrix = [[0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(i + 1, n):
            result = await _get_distance(coords[i], coords[j])
            dist_matrix[i][j] = result["distance_km"]
            dist_matrix[j][i] = result["distance_km"]
            time_matrix[i][j] = result["duration_min"]
            time_matrix[j][i] = result["duration_min"]
    
    # 3. 贪心算法求最优顺序
    # 如果有起点，从起点开始；否则从第一个活动开始
    if start_point:
        # 找到离起点最近的活动作为第一个
        distances_to_start = []
        for coord in coords:
            result = await _get_distance(start_point, coord)
            distances_to_start.append(result["distance_km"])
        start_idx = distances_to_start.index(min(distances_to_start))
    else:
        start_idx = 0
    
    unvisited = set(range(n))
    unvisited.remove(start_idx)
    order = [start_idx]
    current = start_idx
    
    while unvisited:
        next_idx = min(unvisited, key=lambda x: dist_matrix[current][x])
        order.append(next_idx)
        unvisited.remove(next_idx)
        current = next_idx
    
    # 4. 计算总时间和分段详情
    total_distance = 0
    total_time = 0
    segments = []
    
    for i in range(len(order) - 1):
        frm, to = order[i], order[i + 1]
        total_distance += dist_matrix[frm][to]
        total_time += time_matrix[frm][to]
        segments.append({
            "from": names[frm],
            "to": names[to],
            "distance_km": dist_matrix[frm][to],
            "duration_min": time_matrix[frm][to]
        })
    
    # 5. 返回结果
    optimized_activities = [activities[idx] for idx in order]
    
    return {
        "original_order": names,
        "optimized_order": [names[idx] for idx in order],
        "optimized_activities": optimized_activities,
        "total_distance_km": round(total_distance, 1),
        "total_duration_min": round(total_time, 1),
        "total_duration_text": f"{int(total_time)}分钟" if total_time < 60 else f"{int(total_time // 60)}小时{int(total_time % 60)}分钟",
        "segments": segments,
        "suggestion": "建议按优化后的顺序游览" if total_time > 0 else None
    }
if __name__ == "__main__":
    mcp.run(transport="sse")