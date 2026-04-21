from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging

from app.api.v1.schemas.travel import TravelRequest, TravelResponse
from app.services.travel_planner import TravelPlannerService

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# 服务实例
planner_service = TravelPlannerService()

@router.post("/plan", response_model=TravelResponse)
async def plan_travel(travel_request: TravelRequest):
    try:
        # 执行规划
        result_markdown = await planner_service.plan_travel(travel_request)
        
        # 构建响应
        response = TravelResponse(
            session_id=f"session-{datetime.now().timestamp()}",
            status="completed",
            result_markdown=result_markdown,
            created_at=datetime.now()
        )
        
        return response
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"无法连接到 MCP 服务器：{e}")
        raise HTTPException(status_code=503, detail=f"无法连接到 MCP 服务器：{str(e)}")
    except Exception as e:
        logger.error(f"旅行规划执行错误：{e}")
        raise HTTPException(status_code=500, detail=f"内部服务器错误：{str(e)}")