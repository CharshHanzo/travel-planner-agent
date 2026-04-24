from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
import logging

from app.api.v1.schemas.travel import TravelRequest
from app.services.travel_planner import TravelPlannerService

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/stream")
async def agent_stream(request: TravelRequest):
    """Agent 流式规划端点"""
    
    async def event_generator():
        try:
            service = TravelPlannerService()
            async for event in service.plan_travel_stream(request):
                event_type = event["event"]
                event_data = json.dumps(event["data"], ensure_ascii=False)
                yield f"event: {event_type}\ndata: {event_data}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {{\"error\": \"{str(e)}\"}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )