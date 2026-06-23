from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class UserDevice(SQLModel, table=True):
    __tablename__ = "user_devices"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    device_id: str = Field(unique=True, index=True, max_length=255)
    device_name: Optional[str] = Field(default=None, max_length=100)
    last_used_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)