from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    DASHSCOPE_API_KEY: str
    
    # DashScope Configuration
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/api/v1"
    DASHSCOPE_MODEL: str = "qwen-plus"
    
    # MCP Server Configuration
    MCP_SERVER_URL: str = "http://127.0.0.1:8000/sse"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()