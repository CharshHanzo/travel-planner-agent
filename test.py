import os
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

api_key = os.getenv("DASHSCOPE_API_KEY")
# 配置客户端
client = OpenAI(
    api_key=api_key, 
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 百炼的API地址
)

# 发送请求
response = client.chat.completions.create(
    model="qwen-plus-2025-07-28",  # 使用的模型，也可以试试 qwen-max
    messages=[
        {"role": "system", "content": "你是一个 helpful assistant"},
        {"role": "user", "content": "你好，你是什么模型？"}
    ]
)

# 打印回复
print(response.choices[0].message.content)