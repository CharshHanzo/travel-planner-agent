import httpx
import json
import math
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from asyncio import Semaphore
from tenacity import retry, stop_after_attempt, wait_exponential

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 环境变量加载优化
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)
    logger.info(f"已加载配置文件: {env_file}")
else:
    logger.warning(f"未找到配置文件: {env_file}，将使用系统环境变量")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
AMAP_API_KEY = os.getenv("AMAP_API_KEY")

def validate_config() -> bool:
    """验证必要的配置"""
    missing_keys = []
    if not OPENWEATHER_API_KEY:
        missing_keys.append("OPENWEATHER_API_KEY")
    if not AMAP_API_KEY:
        missing_keys.append("AMAP_API_KEY")
    
    if missing_keys:
        logger.warning(f"缺少API配置: {', '.join(missing_keys)}")
        return False
    return True

# 配置区域
FORECAST_BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
GEOCODING_BASE_URL = "http://api.openweathermap.org/geo/1.0/direct"
FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"
AMAP_BASE_URL = "https://restapi.amap.com/v3"

# 全局信号量控制并发
api_semaphore = Semaphore(5)  # 最多5个并发请求

# API 端点
mcp = FastMCP(
    name="Travel Tools Service",
    host="127.0.0.1",
    port=8000,
    stateless_http=True,
    json_response=True,
)

# 辅助函数
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_coordinates(city: str):
    """根据城市名称获取经纬度坐标"""
    logger.info(f"[地理编码] 开始查询城市: {city}")
    
    async with api_semaphore:
        async with httpx.AsyncClient() as client:
            params = {
                "q": city,
                "limit": 1,
                "appid": OPENWEATHER_API_KEY
            }
            response = await client.get(GEOCODING_BASE_URL, params=params)
            
            logger.info(f"[地理编码] API 响应状态: {response.status_code}")
            
            if response.status_code != 200 or not response.json():
                logger.error(f"[地理编码] 未找到城市: {city}")
                return None, None
            
            data = response.json()[0]
            lat, lon = data.get("lat"), data.get("lon")
            logger.info(f"[地理编码] 成功获取坐标: {city} -> ({lat}, {lon})")
            return lat, lon

def parse_date(date_str: str) -> str:
    """解析用户输入的日期"""
    from datetime import datetime, timedelta
    
    logger.info(f"[日期解析] 输入: {date_str}")
    
    if date_str == "明天":
        target_date = datetime.now() + timedelta(days=1)
        result = target_date.strftime("%Y-%m-%d")
        logger.info(f"[日期解析] 明天 -> {result}")
        return result
    elif date_str == "后天":
        target_date = datetime.now() + timedelta(days=2)
        result = target_date.strftime("%Y-%m-%d")
        logger.info(f"[日期解析] 后天 -> {result}")
        return result
    elif date_str == "今天":
        result = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"[日期解析] 今天 -> {result}")
        return result
    
    logger.info(f"[日期解析] 保持原格式: {date_str}")
    return date_str

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def get_weather_by_date(city: str, target_date: str):
    """获取指定日期的天气预报"""
    logger.info(f"[天气查询] 开始查询: city={city}, date={target_date}")
    
    # 1. 获取坐标
    lat, lon = await get_coordinates(city)
    if lat is None:
        logger.error(f"[天气查询] 无法获取坐标: {city}")
        return {"error": f"未找到城市：{city}"}
    
    # 2. 获取5天预报数据
    async with api_semaphore:
        async with httpx.AsyncClient() as client:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "metric",
                "lang": "zh_cn",
                "cnt": 40
            }
            
            logger.info(f"[天气查询] 请求 OpenWeather API: lat={lat}, lon={lon}")
            response = await client.get(FORECAST_BASE_URL, params=params)
        
        logger.info(f"[天气查询] OpenWeather API 响应状态: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"[天气查询] API 请求失败: {response.status_code}")
            return {"error": f"API 请求失败：{response.status_code}"}
        
        data = response.json()
        logger.info(f"[天气查询] 成功获取天气数据，共 {len(data.get('list', []))} 个预报点")
        
        # 3. 查找匹配日期的数据
        target_date_str = parse_date(target_date)
        logger.info(f"[天气查询] 目标日期: {target_date_str}")
        
        for forecast in data["list"]:
            forecast_date = forecast["dt_txt"].split(" ")[0]
            if forecast_date == target_date_str:
                logger.info(f"[天气查询] 找到匹配的天气数据: {forecast_date}")
                return {
                    "city": city,
                    "date": target_date_str,
                    "temperature": forecast["main"]["temp"],
                    "feels_like": forecast["main"]["feels_like"],
                    "humidity": forecast["main"]["humidity"],
                    "pressure": forecast["main"]["pressure"],
                    "wind_speed": forecast["wind"]["speed"],
                    "weather_desc": forecast["weather"][0]["description"],
                    "rain": forecast.get("rain", {}).get("3h", 0)
                }
        
        # 没找到精确匹配
        logger.warning(f"[天气查询] 未找到 {target_date_str} 的预报，使用最近数据")
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
        
        logger.error(f"[天气查询] 完全没有天气数据")
        return {"error": f"未找到{city}的天气预报数据"}

# Weather Agent 工具函数
@mcp.tool()
async def get_weather(city: str, date: str) -> str:
    """获取指定城市在目标日期的天气信息"""
    logger.info(f"[Tool:get_weather] ========== 开始执行 ==========")
    logger.info(f"[Tool:get_weather] 参数: city={city}, date={date}")
    
    # 添加参数验证
    if not city or not city.strip():
        error_msg = "❌ 城市名称不能为空"
        logger.error(f"[Tool:get_weather] {error_msg}")
        return error_msg
    
    if not date:
        error_msg = "❌ 日期不能为空"
        logger.error(f"[Tool:get_weather] {error_msg}")
        return error_msg
    
    try:
        weather_data = await get_weather_by_date(city, date)
        
        if "error" in weather_data:
            error_msg = f"❌ {weather_data['error']}"
            logger.error(f"[Tool:get_weather] 返回错误: {error_msg}")
            return error_msg
        
        # 格式化输出
        note = weather_data.get("note", "")
        rain_info = f"\n☔ 降雨量：{weather_data['rain']} mm" if weather_data.get("rain", 0) > 0 else ""
        
        result = (
            f"📅 {weather_data['date']}{note}\n"
            f"📍 {weather_data['city']}\n"
            f"🌡️ 温度：{weather_data['temperature']}°C（体感 {weather_data['feels_like']}°C）\n"
            f"💧 湿度：{weather_data['humidity']}%\n"
            f"💨 风速：{weather_data['wind_speed']} m/s\n"
            f"🎯 气压：{weather_data['pressure']} hPa\n"
            f"☁️ 天气：{weather_data['weather_desc']}{rain_info}"
        )
        
        logger.info(f"[Tool:get_weather] 执行成功，返回结果长度: {len(result)}")
        logger.info(f"[Tool:get_weather] ========== 执行完成 ==========")
        return result
        
    except Exception as e:
        error_msg = f"❌ 天气查询失败: {str(e)}"
        logger.error(f"[Tool:get_weather] 异常: {e}", exc_info=True)
        return error_msg

# 辅助函数：地址转坐标
async def _geocode(address: str) -> Optional[str]:
    """地址转坐标，返回 '经度,纬度'"""
    logger.info(f"[地理编码] 开始编码地址: {address}")
    
    if not AMAP_API_KEY:
        logger.warning("[地理编码] 未配置高德 API Key")
        return None
    
    async with api_semaphore:
        async with httpx.AsyncClient() as client:
            params = {
                "key": AMAP_API_KEY,
                "address": address
            }
            
            # 尝试详细地址
            response = await client.get(f"{AMAP_BASE_URL}/geocode/geo", params=params)
        
        if response.status_code != 200:
            logger.error(f"[地理编码] API 请求失败: {response.status_code}")
            return None
        
        data = response.json()
        
        if data.get("status") == "1" and data.get("geocodes"):
            location = data["geocodes"][0]["location"]
            logger.info(f"[地理编码] 成功: {address} -> {location}")
            return location
        
        # 如果失败，尝试简化地址（只保留区/县）
        if "区" in address:
            simplified = address.split("区")[0] + "区"
            logger.info(f"[地理编码] 尝试简化地址: {simplified}")
            params["address"] = simplified
            response = await client.get(f"{AMAP_BASE_URL}/geocode/geo", params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "1" and data.get("geocodes"):
                    location = data["geocodes"][0]["location"]
                    logger.info(f"[地理编码] 简化成功: {simplified} -> {location}")
                    return location
    
    logger.warning(f"[地理编码] 所有尝试失败: {address}")
    return None

def get_mock_activities(city: str, keyword: str, limit: int) -> dict:
    """返回模拟数据"""
    logger.info(f"[Mock数据] 生成 {city} 的模拟活动数据")
    
    mock_activities = {
        "广州": [
            {"name": "广州塔", "description": "广州地标建筑，塔高600米，可俯瞰全城美景", "location_hint": "海珠区阅江西路222号", "location": "113.324553,23.106414"},
            {"name": "珠江夜游", "description": "乘坐游船欣赏珠江两岸璀璨夜景", "location_hint": "越秀区沿江路", "location": "113.264385,23.129112"},
            {"name": "陈家祠", "description": "岭南建筑艺术瑰宝，广东民间工艺博物馆", "location_hint": "荔湾区中山七路", "location": "113.248833,23.126272"},
            {"name": "白云山", "description": "广州\"市肺\"，登高望远的好去处", "location_hint": "白云区广园中路", "location": "113.293121,23.185912"},
            {"name": "沙面", "description": "欧陆风情建筑群，拍照打卡圣地", "location_hint": "荔湾区沙面南街", "location": "113.240147,23.109641"}
        ],
        "北京": [
            {"name": "故宫", "description": "明清皇家宫殿，世界文化遗产", "location_hint": "东城区景山前街4号", "location": "116.397128,39.916527"},
            {"name": "长城", "description": "世界七大奇迹之一，中国古代军事防御工程", "location_hint": "延庆区八达岭", "location": "116.014701,40.363369"},
            {"name": "颐和园", "description": "皇家园林博物馆", "location_hint": "海淀区新建宫门路19号", "location": "116.275547,39.999982"}
        ]
    }
    
    activities = mock_activities.get(city, [
        {"name": f"{city}著名景点", "description": f"{city}的知名景点推荐", "location_hint": f"{city}市中心", "location": ""}
    ])[:limit]
    
    return {
        "city": city,
        "keyword": keyword,
        "count": len(activities),
        "activities": activities,
        "source": "模拟数据",
        "note": "💡 提示：使用模拟数据，配置高德地图 API Key 可获取真实数据"
    }


# Activity Agent 工具函数
@mcp.tool()
async def search_activities(city: str, keyword: str = "景点", limit: int = 10) -> dict:
    """搜索目的地的景点、活动、节庆等"""
    logger.info(f"[Tool:search_activities] ========== 开始执行 ==========")
    logger.info(f"[Tool:search_activities] 参数: city={city}, keyword={keyword}, limit={limit}")
    
    try:
        # 使用高德地图 API 作为主要搜索源
        if AMAP_API_KEY:
            logger.info(f"[Tool:search_activities] 使用高德地图 API 搜索")
            async with httpx.AsyncClient() as client:
                params = {
                    "key": AMAP_API_KEY,
                    "keywords": f"{city} {keyword}",
                    "types": "110000",
                    "city": city,
                    "offset": limit,
                    "extensions": "all"
                }
                
                response = await client.get(
                    "https://restapi.amap.com/v3/place/text",
                    params=params
                )
                
                logger.info(f"[Tool:search_activities] 高德 API 响应状态: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "1":
                        pois = data.get("pois", [])
                        logger.info(f"[Tool:search_activities] 找到 {len(pois)} 个结果")
                        
                        activities = []
                        for poi in pois[:limit]:
                            activity = {
                                "name": poi.get("name"),
                                "description": poi.get("type", "暂无描述"),
                                "location_hint": poi.get("address", ""),
                                "location": poi.get("location"),
                                "tel": poi.get("tel", ""),
                                "source": "高德地图"
                            }
                            activities.append(activity)
                            logger.debug(f"[Tool:search_activities] 活动: {activity['name']}")
                        
                        result = {
                            "city": city,
                            "keyword": keyword,
                            "count": len(activities),
                            "activities": activities,
                            "source": "高德地图"
                        }
                        
                        logger.info(f"[Tool:search_activities] 执行成功，返回 {len(activities)} 个活动")
                        logger.info(f"[Tool:search_activities] ========== 执行完成 ==========")
                        return result
        
        # 如果没有 API Key 或搜索失败，返回模拟数据
        logger.warning(f"[Tool:search_activities] 使用模拟数据")
        result = get_mock_activities(city, keyword, limit)
        logger.info(f"[Tool:search_activities] 返回模拟数据，共 {result['count']} 个")
        logger.info(f"[Tool:search_activities] ========== 执行完成 ==========")
        return result
        
    except Exception as e:
        error_result = {
            "error": f"搜索失败: {str(e)}",
            "city": city,
            "keyword": keyword,
            "count": 0,
            "activities": []
        }
        logger.error(f"[Tool:search_activities] 异常: {e}", exc_info=True)
        return error_result

@mcp.tool()
async def plan_route(activities: list, start_point: str = None) -> dict:
    """规划多个活动的游览顺序"""
    logger.info(f"[Tool:plan_route] ========== 开始执行 ==========")
    logger.info(f"[Tool:plan_route] 活动数量: {len(activities)}, 起点: {start_point}")
    
    try:
        if len(activities) < 2:
            result = {
                "error": "至少需要2个活动才能规划路线",
                "optimized_order": [act.get("name", "未知") for act in activities]
            }
            logger.warning(f"[Tool:plan_route] {result['error']}")
            return result
        
        if not AMAP_API_KEY:
            result = {
                "error": "未配置高德地图 API Key，无法计算路线",
                "optimized_order": [act.get("name", "未知") for act in activities],
                "note": "💡 提示：配置高德地图 API Key 可获得真实路线规划"
            }
            logger.warning(f"[Tool:plan_route] {result['error']}")
            return result
        
        # 1. 获取所有活动的坐标
        coords = []
        names = []
        failed = []
        
        for idx, act in enumerate(activities):
            name = act.get("name", f"活动{idx+1}")
            loc = act.get("location", "")
            names.append(name)
            
            logger.info(f"[Tool:plan_route] 处理活动 {idx+1}/{len(activities)}: {name}")
            logger.info(f"[Tool:plan_route] 位置信息: {loc}")
            
            # 判断是坐标还是地址
            if loc and "," in loc and len(loc.split(",")) == 2:
                # 已经是坐标格式
                coords.append(loc)
                logger.info(f"[Tool:plan_route] 直接使用坐标: {loc}")
            elif loc:
                # 需要地理编码
                logger.info(f"[Tool:plan_route] 地址转坐标: {loc}")
                coord = await _geocode(loc)
                if coord:
                    coords.append(coord)
                    logger.info(f"[Tool:plan_route] 编码成功: {loc} -> {coord}")
                else:
                    logger.warning(f"[Tool:plan_route] 编码失败: {name} - {loc}")
                    failed.append(name)
                    coords.append(None)
            else:
                logger.warning(f"[Tool:plan_route] 缺少位置信息: {name}")
                failed.append(name)
                coords.append(None)
        
        if failed:
            error_result = {
                "error": f"无法定位以下活动：{', '.join(failed)}",
                "optimized_order": names,
                "note": "请为这些活动提供更详细的位置信息"
            }
            logger.error(f"[Tool:plan_route] {error_result['error']}")
            return error_result
        
        # 2. 计算距离矩阵（使用高德地图驾车路径规划API）
        logger.info("[Tool:plan_route] 开始计算距离矩阵...")
        n = len(coords)
        dist_matrix = [[0] * n for _ in range(n)]
        time_matrix = [[0] * n for _ in range(n)]
        
        async with httpx.AsyncClient() as client:
            for i in range(n):
                for j in range(i + 1, n):
                    # 使用驾车路径规划 API 代替距离测量 API
                    params = {
                        "key": AMAP_API_KEY,
                        "origin": coords[i],
                        "destination": coords[j],
                        "extensions": "base",  # base 返回基本信息，包括距离和时间
                        "strategy": 0  # 0: 最快路线
                    }
                    
                    url = f"{AMAP_BASE_URL}/direction/driving"
                    logger.info(f"[Tool:plan_route] 计算路径: {names[i]} -> {names[j]}")
                    
                    try:
                        response = await client.get(url, params=params, timeout=10.0)
                        
                        if response.status_code == 200:
                            data = response.json()
                            logger.info(f"[Tool:plan_route] 高德 API 原始响应: {json.dumps(data, ensure_ascii=False)}")
                            
                            if data.get("status") == "1" and data.get("route", {}).get("paths"):
                                path = data["route"]["paths"][0]
                                
                                # 获取距离（米）
                                distance_m = int(path.get("distance", 0))
                                dist_km = round(distance_m / 1000, 1)
                                
                                # 获取时间（秒）
                                duration_s = int(path.get("duration", 0))
                                duration_min = round(duration_s / 60, 1)
                                
                                dist_matrix[i][j] = dist_km
                                dist_matrix[j][i] = dist_km
                                time_matrix[i][j] = duration_min
                                time_matrix[j][i] = duration_min
                                
                                logger.info(f"[Tool:plan_route] 距离: {dist_km}km, 时间: {duration_min}分钟")
                            else:
                                logger.warning(f"[Tool:plan_route] 路径规划失败: {data.get('info', '未知错误')}, 使用估算")
                                # 使用直线距离估算
                                dist_km = estimate_distance(coords[i], coords[j])
                                duration_min = dist_km * 2  # 估算时间
                                dist_matrix[i][j] = dist_km
                                dist_matrix[j][i] = dist_km
                                time_matrix[i][j] = duration_min
                                time_matrix[j][i] = duration_min
                        else:
                            logger.warning(f"[Tool:plan_route] API请求失败: {response.status_code}")
                            # 使用估算距离
                            dist_km = estimate_distance(coords[i], coords[j])
                            duration_min = dist_km * 2
                            dist_matrix[i][j] = dist_km
                            dist_matrix[j][i] = dist_km
                            time_matrix[i][j] = duration_min
                            time_matrix[j][i] = duration_min
                    except Exception as e:
                        logger.error(f"[Tool:plan_route] 路径规划异常: {e}")
                        dist_km = estimate_distance(coords[i], coords[j])
                        duration_min = dist_km * 2
                        dist_matrix[i][j] = dist_km
                        dist_matrix[j][i] = dist_km
                        time_matrix[i][j] = duration_min
                        time_matrix[j][i] = duration_min
        
        # 3. 打印距离矩阵（调试用）
        logger.info("[Tool:plan_route] 距离矩阵:")
        for i in range(n):
            row = [f"{dist_matrix[i][j]:.1f}" for j in range(n)]
            logger.info(f"  {names[i]}: {', '.join(row)}km")
        
        # 4. 使用贪心算法求最优顺序（TSP问题近似解）
        logger.info("[Tool:plan_route] 确定起始点...")
        
        if start_point:
            # 有起点：计算各点到起点的距离
            logger.info(f"[Tool:plan_route] 计算到起点的距离: {start_point}")
            distances_to_start = []
            for coord in coords:
                dist = await get_distance_to_point(start_point, coord, AMAP_API_KEY)
                distances_to_start.append(dist)
            
            # 找到离起点最近的活动
            start_idx = distances_to_start.index(min(distances_to_start))
            logger.info(f"[Tool:plan_route] 起点最近的活动: {names[start_idx]} (距离: {min(distances_to_start)}km)")
        else:
            # 没有起点：从第一个活动开始
            start_idx = 0
            logger.info("[Tool:plan_route] 未指定起点，从第一个活动开始")
        
        # 贪心算法：每次选择最近的下一个点
        unvisited = set(range(n))
        unvisited.remove(start_idx)
        order = [start_idx]
        current = start_idx
        total_distance = 0
        total_time = 0
        
        logger.info(f"[Tool:plan_route] 开始贪心路径规划...")
        logger.info(f"[Tool:plan_route] 起始点: {names[current]}")
        
        while unvisited:
            # 找到未访问中距离当前点最近的点
            next_idx = min(unvisited, key=lambda x: dist_matrix[current][x])
            distance = dist_matrix[current][next_idx]
            travel_time = time_matrix[current][next_idx]
            
            total_distance += distance
            total_time += travel_time
            
            logger.info(f"[Tool:plan_route] {names[current]} -> {names[next_idx]}: {distance}km, {travel_time}分钟")
            
            order.append(next_idx)
            unvisited.remove(next_idx)
            current = next_idx
        
        # 5. 构建分段详情
        segments = []
        for i in range(len(order) - 1):
            frm, to = order[i], order[i + 1]
            segments.append({
                "from": names[frm],
                "to": names[to],
                "distance_km": dist_matrix[frm][to],
                "duration_min": time_matrix[frm][to],
                "duration_text": format_duration(time_matrix[frm][to])
            })
        
        # 6. 构建优化后的活动列表
        optimized_activities = [activities[idx] for idx in order]
        
        # 7. 生成建议
        suggestion = ""
        if total_time > 0:
            if total_time < 60:
                suggestion = f"✅ 优化后总路程 {total_distance}km，预计 {total_time}分钟，建议按此顺序游览"
            else:
                hours = int(total_time // 60)
                minutes = int(total_time % 60)
                suggestion = f"✅ 优化后总路程 {total_distance}km，预计 {hours}小时{minutes}分钟，建议按此顺序游览"
        
        result = {
            "original_order": names,
            "optimized_order": [names[idx] for idx in order],
            "optimized_activities": optimized_activities,
            "total_distance_km": round(total_distance, 1),
            "total_duration_min": round(total_time, 1),
            "total_duration_text": format_duration(total_time),
            "segments": segments,
            "suggestion": suggestion,
            "note": "📊 路线已基于真实驾车距离优化"
        }
        
        logger.info(f"[Tool:plan_route] 规划完成!")
        logger.info(f"[Tool:plan_route] 总距离: {total_distance}km")
        logger.info(f"[Tool:plan_route] 总时间: {total_time}分钟")
        logger.info(f"[Tool:plan_route] 优化顺序: {' -> '.join([names[idx] for idx in order])}")
        logger.info(f"[Tool:plan_route] ========== 执行完成 ==========")
        
        return result
        
    except Exception as e:
        error_msg = f"路线规划失败: {str(e)}"
        logger.error(f"[Tool:plan_route] {error_msg}", exc_info=True)
        return {"error": error_msg}

def estimate_distance(coord1: str, coord2: str) -> float:
    """估算两个坐标之间的直线距离（公里）- 使用Haversine公式"""
    
    def parse_coord(coord):
        lng, lat = map(float, coord.split(','))
        return math.radians(lat), math.radians(lng)
    
    lat1, lon1 = parse_coord(coord1)
    lat2, lon2 = parse_coord(coord2)
    
    # Haversine公式
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    # 地球半径（公里）
    R = 6371
    distance = R * c
    
    return round(distance, 1)

async def get_distance_to_point(start_point: str, dest_point: str, api_key: str) -> float:
    """获取起点到目标点的距离（使用驾车路径规划）"""
    try:
        async with httpx.AsyncClient() as client:
            params = {
                "key": api_key,
                "origin": start_point,
                "destination": dest_point,
                "extensions": "base"
            }
            
            response = await client.get(f"{AMAP_BASE_URL}/direction/driving", params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "1" and data.get("route", {}).get("paths"):
                    distance_m = int(data["route"]["paths"][0].get("distance", 0))
                    return round(distance_m / 1000, 1)
    except Exception as e:
        logger.error(f"[get_distance_to_point] 计算失败: {e}")
    
    # 使用直线距离估算
    return estimate_distance(start_point, dest_point)

def format_duration(minutes: float) -> str:
    """格式化时长"""
    if minutes < 60:
        return f"{int(minutes)}分钟"
    else:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        if mins == 0:
            return f"{hours}小时"
        else:
            return f"{hours}小时{mins}分钟"

@mcp.tool()
async def search_restaurants(
    city: str,
    location: Optional[str] = None,
    keyword: str = "美食",
    budget: Optional[int] = None,
    taste: Optional[str] = None,
    limit: int = 10
) -> dict:
    """搜索餐厅"""
    logger.info(f"[Tool:search_restaurants] ========== 开始执行 ==========")
    logger.info(f"[Tool:search_restaurants] 参数: city={city}, keyword={keyword}, budget={budget}, taste={taste}, limit={limit}")
    
    try:
        if not AMAP_API_KEY:
            logger.warning("[Tool:search_restaurants] 未配置高德 API Key")
            return {
                "error": "未配置高德地图 API Key",
                "note": "💡 提示：请在高德地图开放平台申请 API Key"
            }
        
        # 如果提供了 taste，将其添加到关键词中
        search_keyword = keyword
        if taste:
            search_keyword = f"{taste} {keyword}"
        
        async with httpx.AsyncClient() as client:
            params = {
                "key": AMAP_API_KEY,
                "keywords": f"{city} {search_keyword}",  # 使用增强后的关键词
                "types": "050000",
                "city": city,
                "citylimit": True,
                "offset": limit,
                "page": 1,
                "extensions": "all"
            }
            
            # 如果提供了 location，添加位置相关参数
            if location:
                params["location"] = location  # 中心点坐标 "经度,纬度"
                params["radius"] = 2000  # 搜索半径 2000 米
                params["sortrule"] = "distance"  # 按距离排序
            
            url = f"{AMAP_BASE_URL}/place/text"
            logger.info(f"[Tool:search_restaurants] 请求高德 API: {url}")
            
            response = await client.get(url, params=params)
            logger.info(f"[Tool:search_restaurants] 响应状态: {response.status_code}")
            
            if response.status_code != 200:
                return {"error": f"API 请求失败：{response.status_code}"}
            
            data = response.json()
            
            if data.get("status") != "1":
                return {"error": f"搜索失败：{data.get('info', '未知错误')}"}
            
            pois = data.get("pois", [])
            logger.info(f"[Tool:search_restaurants] 找到 {len(pois)} 个餐厅")
            
            restaurants = []
            for poi in pois:
                cost_str = poi.get("biz_ext", {}).get("cost", "")
                cost = int(float(cost_str)) if cost_str and cost_str != "[]" else 0
                
                if budget and cost > 0 and cost > budget:
                    continue
                
                rating_str = poi.get("biz_ext", {}).get("rating", "")
                rating = float(rating_str) if rating_str and rating_str != "[]" else 0
                
                restaurant = {
                    "id": poi.get("id"),
                    "name": poi.get("name"),
                    "address": poi.get("address"),
                    "location": poi.get("location"),
                    "tel": poi.get("tel", "暂无电话"),
                    "rating": rating,
                    "cost_per_person": cost,
                    "opening_hours": poi.get("opening_hours", "信息待核实"),
                    "type": poi.get("type"),
                    "distance": poi.get("distance", "")
                }
                restaurants.append(restaurant)
                logger.debug(f"[Tool:search_restaurants] 餐厅: {restaurant['name']}, 评分: {rating}, 人均: {cost}")
            
            restaurants.sort(key=lambda x: x.get("rating", 0), reverse=True)
            
            result = {
                "city": city,
                "keyword": keyword,
                "taste": taste,
                "budget": budget,
                "count": len(restaurants),
                "restaurants": restaurants[:limit],
                "note": f"✅ 找到 {len(restaurants)} 家餐厅，已按评分排序"
            }
            
            logger.info(f"[Tool:search_restaurants] 执行成功，返回 {len(restaurants)} 家餐厅")
            logger.info(f"[Tool:search_restaurants] ========== 执行完成 ==========")
            return result
            
    except Exception as e:
        error_msg = f"搜索餐厅失败: {str(e)}"
        logger.error(f"[Tool:search_restaurants] {error_msg}", exc_info=True)
        return {"error": error_msg}

@mcp.tool()
async def recommend_meal_plan(
    activities: list,
    city: str,
    taste: Optional[str] = None,
    budget: Optional[int] = None,
    people_count: int = 2,
    weather_context: Optional[dict] = None
) -> dict:
    """根据活动安排推荐用餐计划（支持天气影响）"""
    logger.info(f"[Tool:recommend_meal_plan] ========== 开始执行 ==========")
    logger.info(f"[Tool:recommend_meal_plan] 参数: city={city}, taste={taste}, budget={budget}, people={people_count}")
    logger.info(f"[Tool:recommend_meal_plan] 天气上下文: {weather_context}")
    logger.info(f"[Tool:recommend_meal_plan] 活动数量: {len(activities)}")
    
    try:
        meal_plan = []
        
        # 确定每餐每人的预算
        if budget:
            per_meal_per_person = budget // people_count // 2
        else:
            per_meal_per_person = None
        
        # 基础搜索关键词
        base_keyword = taste if taste else "美食"
        
        # 根据天气调整推荐策略和关键词
        weather_suggestion = "🌤️ 天气适宜，建议提前预订餐厅"
        weather_keyword_modifier = ""
        
        if weather_context:
            weather_desc = weather_context.get("weather_desc", "").lower()
            temperature = weather_context.get("temperature", 25)
            
            logger.info(f"[Tool:recommend_meal_plan] 分析天气: {weather_desc}, 温度: {temperature}°C")
            
            # 雨天推荐
            if "雨" in weather_desc or "rain" in weather_desc:
                weather_suggestion = "☔ 雨天建议选择有外卖配送或室内餐厅，注意带伞"
                weather_keyword_modifier = ""  # 雨天不修改关键词，只改建议
                logger.info("[Tool:recommend_meal_plan] 应用雨天策略")
            
            # 高温天气推荐
            elif temperature > 30:
                weather_suggestion = "🥵 高温天气，推荐有空调和冷饮的餐厅，建议中午避免户外用餐"
                # 高温时不添加额外关键词，避免搜索无结果
                weather_keyword_modifier = ""
                logger.info("[Tool:recommend_meal_plan] 应用高温策略")
            
            # 寒冷天气推荐
            elif temperature < 10:
                weather_suggestion = "❄️ 寒冷天气，推荐火锅、热汤类餐厅，暖心暖胃"
                # 寒冷时推荐火锅类
                if base_keyword == "美食":
                    base_keyword = "火锅"
                elif "火锅" not in base_keyword:
                    base_keyword = f"{base_keyword} 火锅"
                logger.info("[Tool:recommend_meal_plan] 应用寒冷策略")
            
            # 晴天推荐
            elif "晴" in weather_desc or "clear" in weather_desc:
                weather_suggestion = "☀️ 天气晴朗，推荐有户外座位或景观的餐厅"
                weather_keyword_modifier = ""
                logger.info("[Tool:recommend_meal_plan] 应用晴天策略")
        
        # 存储午餐已推荐的餐厅ID，避免晚餐重复
        lunch_restaurant_ids = []
        
        # 推荐午餐和晚餐
        for meal_type in ["午餐", "晚餐"]:
            # 尝试搜索，如果无结果则降级
            restaurants = []
            search_keywords = [base_keyword]
            
            # 如果基础关键词包含额外修饰词，添加降级关键词
            if " " in base_keyword:
                # 降级到第一个词
                search_keywords.append(base_keyword.split()[0])
            
            for kw in search_keywords:
                if restaurants:
                    break  # 已有结果，停止尝试
                    
                logger.info(f"[Tool:recommend_meal_plan] 尝试搜索关键词: {kw}")
                meal_result = await search_restaurants(
                    city=city,
                    keyword=kw,
                    budget=per_meal_per_person,
                    taste=taste if kw == base_keyword else None,
                    limit=5
                )
                
                if "restaurants" in meal_result and meal_result["restaurants"]:
                    restaurants = meal_result["restaurants"]
                    logger.info(f"[Tool:recommend_meal_plan] 关键词 '{kw}' 找到 {len(restaurants)} 家餐厅")
            
            if restaurants:
                # 如果是晚餐且有午餐记录，过滤掉已推荐的餐厅
                if meal_type == "晚餐" and lunch_restaurant_ids:
                    filtered_restaurants = [
                        r for r in restaurants
                        if r.get("id") not in lunch_restaurant_ids
                    ]
                    if filtered_restaurants:
                        restaurants = filtered_restaurants
                        logger.info(f"[Tool:recommend_meal_plan] 晚餐已过滤午餐餐厅，剩余 {len(restaurants)} 家")
                
                # 取前2家推荐
                recommended = restaurants[:2]
                
                # 记录午餐的餐厅ID
                if meal_type == "午餐":
                    lunch_restaurant_ids = [r.get("id") for r in recommended]
                
                meal_plan.append({
                    "meal": meal_type,
                    "time": "12:00-13:30" if meal_type == "午餐" else "18:00-19:30",
                    "recommended_restaurants": recommended,
                    "suggested_budget": f"{int(budget / people_count / 2)}元/人" if budget else "根据实际情况"
                })
            else:
                # 没有找到餐厅，添加提示
                meal_plan.append({
                    "meal": meal_type,
                    "time": "12:00-13:30" if meal_type == "午餐" else "18:00-19:30",
                    "recommended_restaurants": [],
                    "suggested_budget": f"{int(budget / people_count / 2)}元/人" if budget else "根据实际情况",
                    "note": "⚠️ 未找到符合条件的餐厅，请尝试调整口味或预算"
                })
                logger.warning(f"[Tool:recommend_meal_plan] {meal_type} 未找到餐厅")
        
        result = {
            "city": city,
            "taste": taste,
            "people_count": people_count,
            "total_budget": budget,
            "weather_suggestion": weather_suggestion,
            "meal_plan": meal_plan,
            "note": "💡 提示：建议提前电话确认营业时间和预订情况"
        }
        
        # 如果有天气上下文，添加天气信息到结果
        if weather_context:
            result["weather_used"] = {
                "condition": weather_context.get("weather_desc", "未知"),
                "temperature": weather_context.get("temperature", "未知"),
                "recommendation_basis": weather_suggestion
            }
        
        logger.info(f"[Tool:recommend_meal_plan] 执行成功，推荐 {len([m for m in meal_plan if m['recommended_restaurants']])} 餐")
        logger.info(f"[Tool:recommend_meal_plan] ========== 执行完成 ==========")
        return result
        
    except Exception as e:
        error_msg = f"推荐用餐计划失败: {str(e)}"
        logger.error(f"[Tool:recommend_meal_plan] {error_msg}", exc_info=True)
        return {"error": error_msg}

@mcp.tool()
async def get_restaurant_detail(restaurant_id: str) -> dict:
    """获取餐厅详细信息"""
    logger.info(f"[Tool:get_restaurant_detail] ========== 开始执行 ==========")
    logger.info(f"[Tool:get_restaurant_detail] 餐厅ID: {restaurant_id}")
    
    try:
        if not AMAP_API_KEY:
            return {"error": "未配置高德地图 API Key"}
        
        async with httpx.AsyncClient() as client:
            params = {
                "key": AMAP_API_KEY,
                "id": restaurant_id,
                "extensions": "all"
            }
            
            response = await client.get(f"{AMAP_BASE_URL}/place/detail", params=params)
            
            if response.status_code != 200:
                return {"error": f"API 请求失败：{response.status_code}"}
            
            data = response.json()
            
            if data.get("status") != "1" or not data.get("pois"):
                return {"error": f"未找到餐厅：{restaurant_id}"}
            
            poi = data["pois"][0]
            
            result = {
                "id": poi.get("id"),
                "name": poi.get("name"),
                "address": poi.get("address"),
                "location": poi.get("location"),
                "tel": poi.get("tel", "暂无电话"),
                "opening_hours": poi.get("opening_hours", "信息待核实"),
                "rating": poi.get("biz_ext", {}).get("rating", "暂无评分"),
                "cost_per_person": poi.get("biz_ext", {}).get("cost", "信息待核实"),
                "type": poi.get("type"),
                "recommend": poi.get("recommend", "暂无推荐"),
                "tag": poi.get("tag", "")
            }
            
            logger.info(f"[Tool:get_restaurant_detail] 成功获取餐厅详情: {result['name']}")
            logger.info(f"[Tool:get_restaurant_detail] ========== 执行完成 ==========")
            return result
            
    except Exception as e:
        error_msg = f"获取餐厅详情失败: {str(e)}"
        logger.error(f"[Tool:get_restaurant_detail] {error_msg}", exc_info=True)
        return {"error": error_msg}

@mcp.tool()
async def recommend_by_cuisine(
    city: str,
    cuisine: str,
    location: Optional[str] = None,
    budget: Optional[int] = None,
    limit: int = 5
) -> dict:
    """按菜系推荐餐厅"""
    logger.info(f"[Tool:recommend_by_cuisine] ========== 开始执行 ==========")
    logger.info(f"[Tool:recommend_by_cuisine] 参数: city={city}, cuisine={cuisine}, budget={budget}")
    
    try:
        result = await search_restaurants(
            city=city,
            location=location,
            keyword=cuisine,
            budget=budget,
            limit=limit
        )
        
        if "error" in result:
            return result
        
        final_result = {
            "city": city,
            "cuisine": cuisine,
            "count": result.get("count", 0),
            "recommendations": result.get("restaurants", []),
            "note": f"✅ 为您推荐 {city} 的 {cuisine} 餐厅，已按评分排序"
        }
        
        logger.info(f"[Tool:recommend_by_cuisine] 执行成功，推荐 {final_result['count']} 家餐厅")
        logger.info(f"[Tool:recommend_by_cuisine] ========== 执行完成 ==========")
        return final_result
        
    except Exception as e:
        error_msg = f"推荐失败: {str(e)}"
        logger.error(f"[Tool:recommend_by_cuisine] {error_msg}", exc_info=True)
        return {"error": error_msg}

@mcp.tool()
async def test_connection() -> dict:
    """测试服务器连接和配置状态"""
    logger.info("[Tool:test_connection] 测试连接")
    
    status = {
        "server": "Travel Tools Service",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "api_keys": {
            "openweather": "✅ 已配置" if OPENWEATHER_API_KEY else "❌ 未配置",
            "firecrawl": "✅ 已配置" if FIRECRAWL_API_KEY else "❌ 未配置",
            "amap": "✅ 已配置" if AMAP_API_KEY else "❌ 未配置"
        },
        "available_tools": [
            "get_weather - 查询天气",
            "search_activities - 搜索景点活动",
            "plan_route - 规划路线",
            "search_restaurants - 搜索餐厅",
            "recommend_meal_plan - 推荐用餐计划",
            "get_restaurant_detail - 获取餐厅详情",
            "recommend_by_cuisine - 按菜系推荐"
        ]
    }
    
    logger.info(f"[Tool:test_connection] 返回状态: {status['status']}")
    return status

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("启动 Travel Tools MCP 服务器")
    logger.info(f"OpenWeather API Key: {'✅ 已配置' if OPENWEATHER_API_KEY else '❌ 未配置'}")
    logger.info(f"Firecrawl API Key: {'✅ 已配置' if FIRECRAWL_API_KEY else '❌ 未配置'}")
    logger.info(f"高德地图 API Key: {'✅ 已配置' if AMAP_API_KEY else '❌ 未配置'}")
    logger.info("=" * 60)
    
    mcp.run(transport="sse")