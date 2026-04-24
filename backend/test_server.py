import os
import sys

# 设置 PYTHONPATH
sys.path.insert(0, os.path.abspath('.'))

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.api.v1.router import router as v1_router
    from app.api.v1.endpoints import chat
    
    print("所有模块导入成功")
    print(f"chat 模块的路由: {chat.router.routes}")
    
    app = FastAPI(
        title="Travel Planner API",
        description="API for travel planning application",
        version="1.0.0"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routes
    app.include_router(v1_router, prefix="/api/v1")
    
    # 打印所有路由
    print("所有路由:")
    for route in app.routes:
        print(f"  - {route.path}")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}
    
    print("FastAPI 应用创建成功")
    print("服务器启动中...")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
