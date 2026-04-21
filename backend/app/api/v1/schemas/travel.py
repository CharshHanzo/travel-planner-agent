from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import date, datetime

class TravelRequest(BaseModel):
    city: str = Field(..., description="目的地城市")
    travel_date: date = Field(..., description="出行日期")
    people_count: int = Field(..., ge=1, le=20, description="出行人数")
    budget: int = Field(..., ge=0, description="预算")
    taste: Literal["辣", "清淡", "不挑"] = Field(..., description="口味偏好")
    departure: Optional[str] = Field(None, description="出发地")
    activity_count: int = Field(3, ge=2, le=5, description="每天活动数量")
    
    @field_validator('travel_date')
    @classmethod
    def validate_travel_date(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("出行日期不能是过去的日期")
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "city": "上海",
                "travel_date": "2026-05-01",
                "people_count": 2,
                "budget": 5000,
                "taste": "不挑",
                "departure": "北京",
                "activity_count": 3
            }
        }
    }

class TravelResponse(BaseModel):
    session_id: str = Field(..., description="会话ID")
    status: str = Field(..., description="状态")
    result_markdown: Optional[str] = Field(None, description="规划结果Markdown")
    created_at: datetime = Field(..., description="创建时间")

class AgentStatusEvent(BaseModel):
    agent_name: str = Field(..., description="Agent名称")
    status: Literal["pending", "running", "completed", "error"] = Field(..., description="状态")
    message: str = Field(..., description="状态消息")
    timestamp: datetime = Field(..., description="时间戳")