from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class LearnedPreference(SQLModel, table=True):
    __tablename__ = "learned_preferences"
    
    id: int = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    preference_type: str = Field(max_length=50, description="偏好类型: taste/budget/activity/season")
    value: str = Field(description="偏好值 JSON")
    confidence: float = Field(default=0.0, ge=0, le=1, description="置信度 0-1")
    source_trips: str = Field(default="[]", description="来源行程ID列表 JSON")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)