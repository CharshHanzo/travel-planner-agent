import httpx
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv
load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
# 配置区域
FORECAST_BASE_URL = "https://api.openweathermap.org/data/2.5/forecast"
GEOCODING_BASE_URL = "http://api.openweathermap.org/geo/1.0/direct"

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




# MCP 工具函数
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


if __name__ == "__main__":
    mcp.run(transport="sse")