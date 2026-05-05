from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class TripEmbedding(SQLModel, table=True):
    __tablename__ = "trip_embeddings"
    
    id: int = Field(default=None, primary_key=True)
    trip_id: str = Field(foreign_key="trips.id", unique=True, description="关联行程ID")
    embedding: str = Field(description="向量数据 JSON 字符串")
    model_name: str = Field(default="text-embedding-v3", max_length=100, description="使用的 Embedding 模型")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)