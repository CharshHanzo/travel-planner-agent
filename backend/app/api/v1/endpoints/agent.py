from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
import logging

from app.api.v1.schemas.travel import TravelRequest
from app.services.travel_planner import TravelPlannerService

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# 服务实例
planner_service = TravelPlannerService()

@router.post("/stream")
async def stream_agent_status(request: Request, travel_request: TravelRequest):
    async def event_generator():
        async for event in planner_service.plan_travel_stream(travel_request):
            if await request.is_disconnected():
                break
            yield f"event: {event['event']}\n"
            yield f"data: {json.dumps(event['data'])}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")