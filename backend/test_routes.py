import os
import sys

# 设置 PYTHONPATH
sys.path.insert(0, os.path.abspath('.'))

try:
    from fastapi import FastAPI
    from app.api.v1.router import router as v1_router
    from app.api.v1.endpoints import chat
    
    print("所有模块导入成功")
    print(f"chat 模块的路由: {chat.router.routes}")
    
    app = FastAPI()
    
    # Register routes
    app.include_router(v1_router, prefix="/api/v1")
    
    # 打印所有路由
    print("所有路由:")
    for route in app.routes:
        print(f"  - {route.path}")
    
    print("路由测试完成")
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
