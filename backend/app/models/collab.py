from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class CollabRoom(SQLModel, table=True):
    __tablename__ = "collab_rooms"
    
    id: str = Field(default=None, primary_key=True)
    creator_id: str = Field(foreign_key="users.id")
    participant_ids: str = Field(default="[]", description="参与用户ID列表 JSON")
    trip_ids: str = Field(default="[]", description="关联行程ID列表 JSON")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)