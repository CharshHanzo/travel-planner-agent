from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
import uuid

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    device_id: str = Field(index=True, unique=True, description="设备唯一标识")
    nickname: Optional[str] = Field(default=None, max_length=50)
    preference_version: int = Field(default=1, description="偏好模型版本号")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)