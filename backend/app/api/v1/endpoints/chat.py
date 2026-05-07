from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
import asyncio
import json
import uuid
import logging
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.agents.graph import ChatSupervisor
from app.db import get_session
from app.services.user_service import get_or_create_user
from app.services.trip_service import upsert_trip

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# 会话存储
sessions: Dict[str, Dict[str, Any]] = {}

# ChatSupervisor 实例
chat_supervisor = ChatSupervisor()

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID（首次为空，后端生成返回）")
    context: Optional[Dict[str, Any]] = Field({}, description="对话上下文")
    device_id: Optional[str] = Field(None, description="设备唯一标识")

async def stream_response(request: Request, message: str, session_id: str, context: Dict[str, Any], device_id: Optional[str] = None, db_session: Session = None):
    """流式返回响应"""
    try:
        # 初始化消息列表
        if "messages" not in context:
            context["messages"] = []
        
        # 追加用户消息
        context["messages"].append({
            "role": "user",
            "content": message,
            "timestamp": int(time.time()),
        })
        
        # 发送 thinking 事件
        yield f"event: thinking\ndata: {{}}\n\n"
        
        # 调用 ChatSupervisor 处理消息
        response, updated_context = chat_supervisor.process_message(message, context)
        
        # 判断这次调用了哪些 Agent（从意图推断）
        intent = updated_context.get("last_intent", "general")
        agent_calls = []
        if intent == "weather":
            agent_calls = ["weather"]
        elif intent == "activities":
            agent_calls = ["activities"]
        elif intent == "food":
            agent_calls = ["food"]
        elif intent == "generate_plan":
            agent_calls = ["weather", "activities", "food"]
        elif intent == "modify":
            agent_calls = ["modify"]
        
        # 追加 AI 消息
        updated_context["messages"].append({
            "role": "assistant",
            "content": response,
            "agent_calls": agent_calls,
            "timestamp": int(time.time()),
        })
        
        # ⚠️ 关键：立即更新 sessions，确保后续消息能读到最新上下文
        sessions[session_id] = updated_context
        
        # 判断是否为计划消息
        is_plan = response.strip().startswith("# 最终行程建议")
        
        # 发送 message 事件
        response_data = json.dumps({"text": response}, ensure_ascii=False)
        yield f"event: message\ndata: {response_data}\n\n"
        
        # 如果是计划，发送 plan 事件
        if is_plan:
            yield f"event: plan\ndata: {response_data}\n\n"
        
        # 发送 session 事件
        yield f"event: session\ndata: {{\"session_id\": \"{session_id}\"}}\n\n"
        
        # === 宽松保存逻辑（更新消息列表到 conversation_context）===
        if device_id and db_session:
            try:
                city = updated_context.get('city', '')
                prefs = updated_context.get('preferences', {})
                travel_date = prefs.get('date', '')
                people_count = prefs.get('people', 1)
                budget = prefs.get('budget', 0)
                taste = prefs.get('taste', '')
                
                # 获取或创建用户
                user = get_or_create_user(db_session, device_id)
                
                # 创建或更新行程记录
                upsert_trip(
                    session=db_session,
                    user_id=user.id,
                    session_id=session_id,
                    city=city,
                    travel_date=travel_date,
                    people_count=people_count,
                    budget=budget,
                    taste=taste,
                    plan_markdown=response if is_plan else None,
                    weather_data=json.dumps(updated_context.get('weather'), ensure_ascii=False) if updated_context.get('weather') else None,
                    activities_data=json.dumps(updated_context.get('activities'), ensure_ascii=False) if updated_context.get('activities') else None,
                    food_data=json.dumps(updated_context.get('food'), ensure_ascii=False) if updated_context.get('food') else None,
                    messages=updated_context.get("messages", []),  # 新增：传入消息列表
                    mode="chat",
                )
                logger.info(f"对话规划行程已保存/更新，用户: {user.id}, 城市: {city}, session_id: {session_id}")
            except Exception as save_error:
                logger.error(f"保存行程失败：{save_error}")
        
        # 发送 done 事件
        yield f"event: done\ndata: {{}}\n\n"
        
    except Exception as e:
        logger.error(f"对话处理错误：{e}")
        yield f"event: error\ndata: {{\"message\": \"{str(e)}\"}}\n\n"
        yield f"event: done\ndata: {{}}\n\n"

@router.post("/plan-chat")
async def plan_chat(request: Request, chat_request: ChatRequest, db_session: Session = Depends(get_session)):
    """对话式规划接口（SSE 流式）"""
    try:
        # 处理会话 ID
        if not chat_request.session_id:
            # 生成新的会话 ID
            session_id = f"session-{uuid.uuid4()}"
            # 初始化上下文
            context = {
                "city": None,
                "weather": None,
                "activities": None,
                "food": None,
                "preferences": {
                    "budget": None,
                    "taste": None,
                    "date": None,
                    "people": None,
                }
            }
        else:
            # 使用现有会话 ID
            session_id = chat_request.session_id
            # 读取现有上下文
            context = sessions.get(session_id, {
                "city": None,
                "weather": None,
                "activities": None,
                "food": None,
                "preferences": {
                    "budget": None,
                    "taste": None,
                    "date": None,
                    "people": None,
                }
            })
        
        # 合并前端传入的上下文（如果有）
        if chat_request.context:
            context.update(chat_request.context)
        
        # 返回流式响应
        return StreamingResponse(
            stream_response(request, chat_request.message, session_id, context, chat_request.device_id, db_session),
            media_type="text/event-stream"
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"无法连接到 MCP 服务器：{e}")
        raise HTTPException(status_code=503, detail=f"无法连接到 MCP 服务器：{str(e)}")
    except Exception as e:
        logger.error(f"对话规划执行错误：{e}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误：{str(e)}")
