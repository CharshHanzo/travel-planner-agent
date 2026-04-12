from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    name="Weather Service",
    host="127.0.0.1",
    port=8000,
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def get_weather(city: str, date: str) -> str:
    """获取指定城市在目标日期的天气信息。"""
    weather_map = {
        "广州": "广州，25°C，多云",
        "上海": "上海，22°C，小雨",
        "北京": "北京，18°C，晴",
        "杭州": "杭州，23°C，阴",
    }
    base = weather_map.get(city, f"{city}，24°C，晴间多云")
    return f"{date} 天气：{base}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
