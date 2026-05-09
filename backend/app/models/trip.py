from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import uuid

class Trip(SQLModel, table=True):
    __tablename__ = "trips"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True, description="关联用户ID")
    
    city: str = Field(max_length=100, description="目的地城市")
    travel_date: str = Field(max_length=10, description="出发日期 YYYY-MM-DD")
    people_count: int = Field(default=1, description="人数")
    budget: int = Field(default=0, description="预算金额")
    taste: Optional[str] = Field(default=None, max_length=10, description="口味偏好")
    departure: Optional[str] = Field(default=None, max_length=100, description="出发地点")
    activity_count: Optional[int] = Field(default=3, description="活动数量")
    
    plan_markdown: str = Field(default="", description="完整旅行计划 Markdown")
    weather_data: Optional[str] = Field(default=None, description="WeatherAgent JSON 结果")
    activities_data: Optional[str] = Field(default=None, description="ActivityAgent JSON 结果")
    food_data: Optional[str] = Field(default=None, description="FoodAgent JSON 结果")
    conversation_context: Optional[str] = Field(default=None, description="对话上下文 JSON")
    coordinates_data: Optional[str] = Field(default=None, description="坐标数据 JSON")
    
    semantic_text: Optional[str] = Field(default=None, description="预生成的语义摘要文本")
    
    rating: Optional[float] = Field(default=None, ge=0, le=5, description="用户评分 0-5")
    is_liked: bool = Field(default=False, description="用户点赞")
    modify_count: int = Field(default=0, description="修改次数")
    
    mode: str = Field(default="quick", max_length=20, description="规划模式: quick / chat")
    
    is_deleted: bool = Field(default=False, index=True, description="软删除标记")
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)