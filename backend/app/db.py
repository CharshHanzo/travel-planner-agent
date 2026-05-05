from sqlmodel import SQLModel, Session, create_engine
from app.core.config import settings
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'travel_history.db')}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session