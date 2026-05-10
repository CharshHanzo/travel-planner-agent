from sqlmodel import SQLModel, Field
from datetime import datetime, timezone, timedelta
from typing import Optional
import uuid

# 中国时区
CST = timezone(timedelta(hours=8))

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    device_id: str = Field(index=True, unique=True, description="设备唯一标识")
    nickname: Optional[str] = Field(default=None, max_length=50)
    preference_version: int = Field(default=1, description="偏好模型版本号")
    created_at: datetime = Field(default_factory=lambda: datetime.now(CST))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(CST))