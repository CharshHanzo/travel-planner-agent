"""应用配置管理"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Settings(BaseSettings):
    """应用配置类"""
    
    # LLM Provider Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "xiaomi")  # dashscope, xiaomi
    
    # DashScope (通义千问) 配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL: str = os.getenv(
        "DASHSCOPE_BASE_URL", 
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    DASHSCOPE_MODEL: str = os.getenv("DASHSCOPE_MODEL", "")
    
    # XIAOMI 配置
    XIAOMI_API_KEY: str = os.getenv("XIAOMI_API_KEY", "")
    XIAOMI_BASE_URL: str = os.getenv(
        "XIAOMI_BASE_URL", 
        "https://token-plan-cn.xiaomimimo.com/v1"
    )
    XIAOMI_MODEL: str = os.getenv("XIAOMI_MODEL", "MiMo-V2.5")
    
    # MCP Server 配置
    MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/sse")
    
    # 应用配置
    APP_NAME: str = "Travel Planner API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS 配置
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # 超时配置（秒）
    AGENT_TIMEOUT: int = 60
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()


# 验证必要配置
def validate_config() -> bool:
    """验证必要的配置是否存在"""
    missing = []
    
    if settings.LLM_PROVIDER == "dashscope":
        if not settings.DASHSCOPE_API_KEY:
            missing.append("DASHSCOPE_API_KEY")
    elif settings.LLM_PROVIDER == "xiaomi":
        if not settings.XIAOMI_API_KEY:
            missing.append("XIAOMI_API_KEY")
    else:
        raise ValueError(f"不支持的LLM提供商: {settings.LLM_PROVIDER}")
    
    if missing:
        raise ValueError(f"缺少必要的环境变量: {', '.join(missing)}")
    
    return True