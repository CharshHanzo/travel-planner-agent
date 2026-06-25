from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import logging
from sqlmodel import Session
import json
from typing import Optional
import re
import functools

from app.api.v1.schemas.travel import TravelRequest
from app.services.user_service import get_or_create_user
from app.services.trip_service import create_trip
from app.db import get_session, engine as db_engine
from app.utils.coordinates import extract_coordinates, format_coordinates_for_frontend, remove_coordinates_json
from app.services.learning_engine import LearningEngine
from app.models.user import User
from app.core.dependencies import get_current_user
from app.agents.tools import get_mcp_tools, wrap_mcp_tools, run_async
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from app.agents.prompts import WEATHER_AGENT_PROMPT, ACTIVITY_AGENT_PROMPT, FOOD_AGENT_PROMPT, ROUTE_AGENT_PROMPT
from app.core.config import settings
from langchain_core.messages import HumanMessage

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()


@functools.lru_cache(maxsize=1)
def _get_agents():
    """获取所有 Agent 实例（缓存）"""
    mcp_tools = run_async(get_mcp_tools())
    sync_tools = wrap_mcp_tools(mcp_tools)
    
    model = ChatOpenAI(
        model=settings.DASHSCOPE_MODEL,
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL,
        temperature=0.5,
    )
    
    weather_agent = create_react_agent(
        model=model,
        tools=[t for t in sync_tools if t.name == 'get_weather'],
        name="WeatherAgent",
        prompt=WEATHER_AGENT_PROMPT,
    )
    
    activity_agent = create_react_agent(
        model=model,
        tools=[t for t in sync_tools if t.name == 'search_activities'],
        name="ActivityAgent",
        prompt=ACTIVITY_AGENT_PROMPT,
    )
    
    food_agent = create_react_agent(
        model=model,
        tools=[t for t in sync_tools if t.name == 'search_restaurants'],
        name="FoodAgent",
        prompt=FOOD_AGENT_PROMPT,
    )
    
    route_agent = create_react_agent(
        model=model,
        tools=[t for t in sync_tools if t.name == 'plan_route'],
        name="RouteAgent",
        prompt=ROUTE_AGENT_PROMPT,
    )
    
    return weather_agent, activity_agent, food_agent, route_agent, model


@router.post("/plan")
async def plan_travel(
    travel_request: TravelRequest,
    session: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user),
):
    """快速规划（SSE 流式返回，实时进度）"""
    
    async def generate():
        try:
            weather_agent, activity_agent, food_agent, route_agent, model = _get_agents()
            
            city = travel_request.city
            date = travel_request.travel_date.isoformat() if hasattr(travel_request.travel_date, 'isoformat') else str(travel_request.travel_date)
            people = travel_request.people_count
            budget = travel_request.budget
            taste = travel_request.taste
            transport_mode = travel_request.transport_mode or "any"
            departure = travel_request.departure or ""
            
            # 1. WeatherAgent
            yield f"event: agent_start\ndata: {json.dumps({'agent':'weather'})}\n\n"
            weather_input = f"获取 {city} 在 {date} 的天气信息"
            weather_result = weather_agent.invoke({"messages": [HumanMessage(content=weather_input)]})
            weather_text = weather_result["messages"][-1].content
            yield f"event: agent_end\ndata: {json.dumps({'agent':'weather'})}\n\n"
            
            # 2. ActivityAgent
            yield f"event: agent_start\ndata: {json.dumps({'agent':'activities'})}\n\n"
            activity_input = f"推荐 {city} 的景点和活动，人数{people}，日期{date}，出发地点：{departure}，出行方式：{transport_mode}，天气参考：{weather_text}"
            activity_result = activity_agent.invoke({"messages": [HumanMessage(content=activity_input)], "limit": 5})
            activity_text = activity_result["messages"][-1].content
            yield f"event: agent_end\ndata: {json.dumps({'agent':'activities'})}\n\n"
            
            # 3. FoodAgent
            yield f"event: agent_start\ndata: {json.dumps({'agent':'food'})}\n\n"
            food_input = f"推荐 {city} 的美食和餐厅，口味{taste}，预算{budget}元，{people}人，位置优先靠近：{departure}，出行方式：{transport_mode}，活动参考：{activity_text}"
            food_result = food_agent.invoke({"messages": [HumanMessage(content=food_input)], "limit": 5})
            food_text = food_result["messages"][-1].content
            yield f"event: agent_end\ndata: {json.dumps({'agent':'food'})}\n\n"
            
            # 4. RouteAgent
            yield f"event: agent_start\ndata: {json.dumps({'agent':'route'})}\n\n"
            route_input = f"规划路线，起点：{departure}，出行方式：{transport_mode}，活动：{activity_text}，餐厅：{food_text}"
            route_result = route_agent.invoke({"messages": [HumanMessage(content=route_input)]})
            route_text = route_result["messages"][-1].content
            yield f"event: agent_end\ndata: {json.dumps({'agent':'route'})}\n\n"
            
            # 5. 汇总生成计划
            yield f"event: agent_start\ndata: {json.dumps({'agent':'plan'})}\n\n"
            summary_prompt = f"""请根据以下信息生成最终的旅行计划，使用 Markdown 格式：
城市：{city}，日期：{date}，人数：{people}，预算：{budget}元，口味：{taste}
天气信息：{weather_text}
活动信息：{activity_text}
餐饮信息：{food_text}
路线信息：{route_text}

最终答复要求：
1. 使用 Markdown
2. 以 # 最终行程建议 开头
3. 包含：天气与出行提醒、活动建议、餐饮建议、推荐行程、预算建议
4. 【重要】末尾必须附加一个坐标 JSON 块，格式如下：
```json
{{
  "coordinates": {{
    "activities": [{{"name": "景点名", "location": "经度,纬度"}}],
    "restaurants": [{{"name": "餐厅名", "location": "经度,纬度"}}],
    "route": {{"path": ["起点经度,纬度", "终点经度,纬度"]}}
  }}
}}
坐标信息从活动和路线中提取，route_text 中的坐标必须包含在内。
"""
            summary_prompt += f"\n路线坐标参考：{route_text[:500]}"
            final_response = model.invoke(summary_prompt).content
            
            coordinates = extract_coordinates(final_response)
            result_markdown = remove_coordinates_json(final_response)
            formatted_coords = format_coordinates_for_frontend(coordinates) if coordinates else None
            
            if not formatted_coords or not isinstance(formatted_coords, dict) or not formatted_coords.get("points"):
                formatted_coords = _extract_coords_from_markdown(final_response)
            
            yield f"event: plan\ndata: {json.dumps({'markdown': result_markdown, 'coordinates': formatted_coords}, ensure_ascii=False)}\n\n"
            yield f"event: agent_end\ndata: {json.dumps({'agent':'plan'})}\n\n"
            
            # 保存行程
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
                transport_mode=transport_mode,
                plan_markdown=result_markdown,
                mode="quick",
                coordinates_data=json.dumps(coordinates, ensure_ascii=False) if coordinates else None,
            )
            logger.info(f"行程已保存，trip_id={trip.id}")
            
            # 学习更新
            try:
                with Session(db_engine) as learning_session:
                    engine = LearningEngine(learning_session)
                    if current_user:
                        engine.update_user_preferences(current_user.id)
            except Exception as e:
                logger.error(f"更新用户偏好失败: {e}")
            
            yield f"event: done\ndata: {json.dumps({})}\n\n"
            
        except Exception as e:
            logger.error(f"旅行规划执行错误：{e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


def _extract_coords_from_markdown(markdown: str) -> dict:
    """从 Markdown 文本中直接提取坐标（后备方案）"""
    points = []
    
    # 匹配格式：(113.245,23.115) 或 113.245,23.115
    coord_pattern = r'\(?(\d{2,3}\.\d{3,4}),\s*(\d{2,3}\.\d{3,4})\)?'
    matches = re.findall(coord_pattern, markdown)
    
    # 匹配景点和餐厅名称
    for i, (lng, lat) in enumerate(matches):
        # 找坐标前面的文本作为名称
        name = f"地点{i+1}"
        points.append({
            "name": name,
            "lng": float(lng),
            "lat": float(lat),
            "type": "activity",
        })
    
    return {
        "points": points,
        "route": None,
    }
