# Function Calling 入门：让模型调用工具
# 学习计划 Day 2 —— agent 的核心机制（决策 → 执行 → 反馈）
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# ===== 1. 给模型"工具箱"：声明工具有什么、参数是什么 =====
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如：北京"}
                },
                "required": ["city"],
            },
        },
    }
]

# ===== 2. 工具的真实执行函数（模型不会执行，是我们来跑）=====
def get_weather(city):
    # 模拟数据（演示用，不是真实天气）
    weather_map = {"北京": "晴，26°C", "上海": "多云，28°C", "广州": "小雨，30°C"}
    return weather_map.get(city, f"{city}：天气数据暂缺")

# ===== 3. 开始对话 =====
messages = [
    {"role": "system", "content": "你是一个智能助手，可以使用工具查询天气。"},
    {"role": "user", "content": "上海和广州今天哪个更热？"},
]

# 第一次请求：模型会判断是否需要调用工具
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=messages,
    tools=tools,
)

message = response.choices[0].message

# ===== 4. 检查模型是否想调用工具 =====
if message.tool_calls:
    # 关键：assistant 的工具调用消息只添加一次（API 协议要求）
    messages.append(message)
    for tool_call in message.tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        print(f"① 模型请求调用工具：{name}({args})")

        # 我们执行工具
        result = get_weather(**args)
        print(f"② 工具执行结果：{result}")

        # 每条工具调用对应一条 tool 消息回传
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": str(result),
        })

    # 第二次请求：模型根据工具结果生成最终回答
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        tools=tools,
    )
    print(f"③ 模型最终回答：{response.choices[0].message.content}")
else:
    print("模型直接回答了（没调用工具）：", message.content)
