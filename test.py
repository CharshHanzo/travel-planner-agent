import os
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI

# LLM Provider Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "xiaomi")  # dashscope, xiaomi

if LLM_PROVIDER == "dashscope":
    # DashScope Configuration
    api_key = os.getenv("DASHSCOPE_API_KEY")
    model_name = os.getenv("DASHSCOPE_MODEL", "qwen-plus-2025-07-28")
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
elif LLM_PROVIDER == "xiaomi":
    # XIAOMI Configuration
    api_key = os.getenv("XIAOMI_API_KEY")
    model_name = os.getenv("XIAOMI_MODEL", "MiMo-V2.5")
    base_url = "https://token-plan-cn.xiaomimimo.com/v1"
else:
    raise ValueError(f"不支持的LLM提供商: {LLM_PROVIDER}")

# 创建LLM客户端
client = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url,
    temperature=0.7,
)

# 发送请求
response = client.invoke("你好，你是什么模型？")
print(f"LLM Provider: {LLM_PROVIDER}")
print(f"Model: {model_name}")
print(f"Response: {response.content}")