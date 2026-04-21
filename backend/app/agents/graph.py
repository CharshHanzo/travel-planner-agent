import logging
import functools

from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor
from langchain_openai import ChatOpenAI

from app.agents.tools import get_mcp_tools, wrap_mcp_tools, run_async
from app.agents.prompts import SUPERVISOR_PROMPT, WEATHER_AGENT_PROMPT, ACTIVITY_AGENT_PROMPT, FOOD_AGENT_PROMPT
from app.core.config import settings

# 配置日志
logger = logging.getLogger(__name__)

@functools.lru_cache(maxsize=1)
def build_travel_graph():
    """构建并返回编译后的 LangGraph 主管图"""
    
    # 获取 MCP 工具
    mcp_tools = run_async(get_mcp_tools())
    
    logger.info(f"加载了 {len(mcp_tools)} 个 MCP 工具")
    
    if not mcp_tools:
        logger.warning("没有加载到任何工具，将使用无工具的 Agent")

    # 创建模型
    model = ChatOpenAI(
        model=settings.DASHSCOPE_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL,
        temperature=0.5,
    )

    # 包装所有 MCP 工具为同步工具
    sync_tools = wrap_mcp_tools(mcp_tools)
    
    # 创建 WeatherAgent
    weather_tools = [t for t in sync_tools if t.name == 'get_weather']
    weather_agent = create_react_agent(
        model=model,
        tools=weather_tools,
        name="WeatherAgent",
        prompt=WEATHER_AGENT_PROMPT,
    )
    
    # 创建 ActivityAgent
    activity_tools = [t for t in sync_tools if t.name in ['search_activities', 'plan_route']]
    activity_agent = create_react_agent(
        model=model,
        tools=activity_tools,
        name="ActivityAgent",
        prompt=ACTIVITY_AGENT_PROMPT,
    )
    
    # 创建 FoodAgent
    food_tools = [t for t in sync_tools if t.name in [
        'search_restaurants',
        'recommend_meal_plan',
        'get_restaurant_detail',
        'recommend_by_cuisine'
    ]]
    food_agent = create_react_agent(
        model=model,
        tools=food_tools,
        name="FoodAgent",
        prompt=FOOD_AGENT_PROMPT,
    )

    # 创建 Supervisor
    workflow = create_supervisor(
        [weather_agent, activity_agent, food_agent],
        model=model,
        prompt=SUPERVISOR_PROMPT,
        output_mode="last_message",
        parallel_tool_calls=False,
        supervisor_name="TravelSupervisor",
    )
    
    return workflow.compile(name="travel_planner_supervisor")