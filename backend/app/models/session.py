from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class Session(SQLModel, table=True):
    __tablename__ = "sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    refresh_token: str = Field(unique=True, index=True, max_length=500)
    expires_at: datetime = Field()
    created_at: datetime = Field(default_factory=datetime.utcnow)