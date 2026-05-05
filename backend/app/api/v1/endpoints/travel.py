from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import logging
from sqlmodel import Session

from app.api.v1.schemas.travel import TravelRequest, TravelResponse
from app.services.travel_planner import TravelPlannerService
from app.services.user_service import get_or_create_user
from app.services.trip_service import create_trip
from app.db import get_session

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter()

# 服务实例
planner_service = TravelPlannerService()

@router.post("/plan", response_model=TravelResponse)
async def plan_travel(travel_request: TravelRequest, session: Session = Depends(get_session)):
    try:
        # 执行规划
        result_markdown = await planner_service.plan_travel(travel_request)
        
        # 获取或创建用户
        user = get_or_create_user(session, travel_request.device_id)
        
        # 保存行程记录
        trip = create_trip(
            session=session,
            user_id=user.id,
            city=travel_request.city,
            travel_date=travel_request.travel_date.isoformat(),
            people_count=travel_request.people_count,
            budget=travel_request.budget,
            taste=travel_request.taste,
            departure=travel_request.departure,
            activity_count=travel_request.activity_count,
            plan_markdown=result_markdown,
            mode="quick",
        )
        
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