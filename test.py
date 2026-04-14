import os
from dotenv import load_dotenv
load_dotenv()
from langchain_openai import ChatOpenAI  # 改用 ChatOpenAI

api_key = os.getenv("DASHSCOPE_API_KEY")

# 直接使用 ChatOpenAI，配置百炼的兼容接口
client = ChatOpenAI(
    model="qwen-plus-2025-07-28",      # 模型名称
    api_key=api_key,                   # 百炼的API Key
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 百炼API地址
    temperature=0.7,                   # 可选：控制随机性
)

# 发送请求
response = client.invoke("你好，你是什么模型？")
print(response.content)