from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
import uuid
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.agents.graph import ChatSupervisor

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

async def stream_response(request: Request, message: str, session_id: str, context: Dict[str, Any]):
    """流式返回响应"""
    try:
        # 发送 thinking 事件
        yield f"event: thinking\ndata: {{}}\n\n"
        
        # 调用 ChatSupervisor 处理消息
        response, updated_context = chat_supervisor.process_message(message, context)
        
        # ⚠️ 关键：立即更新 sessions，确保后续消息能读到最新上下文
        sessions[session_id] = updated_context
        
        # 发送 message 事件
        response_data = json.dumps({"text": response}, ensure_ascii=False)
        yield f"event: message\ndata: {response_data}\n\n"
        
        # 发送 session 事件
        yield f"event: session\ndata: {{\"session_id\": \"{session_id}\"}}\n\n"
        
        # 发送 done 事件
        yield f"event: done\ndata: {{}}\n\n"
        
    except Exception as e:
        logger.error(f"对话处理错误：{e}")
        yield f"event: error\ndata: {{\"message\": \"{str(e)}\"}}\n\n"
        yield f"event: done\ndata: {{}}\n\n"

@router.post("/plan-chat")
async def plan_chat(request: Request, chat_request: ChatRequest):
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
            stream_response(request, chat_request.message, session_id, context),
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
