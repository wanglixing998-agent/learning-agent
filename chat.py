# 第一个大模型对话脚本：调用 DeepSeek
# 学习计划 Day 2 —— 大模型 API 入门
import os
from dotenv import load_dotenv
from openai import OpenAI

# 从 .env 文件加载 API Key
load_dotenv()

# 创建客户端（DeepSeek 兼容 OpenAI 接口格式）
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# 发起一次对话：system 设定角色，user 是提问
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=[

        {"role": "system", "content": "你是一个乐于助人的中文助手。"},
        {"role": "user", "content": "什么是函数？"},
    ],
    temperature=0.7,
)

# 打印模型的回复
print(response.choices[0].message.content)
