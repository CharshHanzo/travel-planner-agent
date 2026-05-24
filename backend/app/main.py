from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.v1.router import router as v1_router
from app.db import init_db

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Travel Planner API",
    description="API for travel planning application",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def on_startup():
    init_db()
    
    logger.info("正在加载 MCP 工具...")
    from app.agents.tools import get_mcp_tools, wrap_mcp_tools, run_async
    mcp_tools = await get_mcp_tools()
    sync_tools = wrap_mcp_tools(mcp_tools)
    logger.info(f"加载了 {len(sync_tools)} 个 MCP 工具")
    
    from app.api.v1.endpoints.chat import chat_supervisor
    chat_supervisor.initialize(sync_tools)
    logger.info("MCP 工具加载完成")