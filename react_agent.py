# ReAct Agent 第一版：自动思考-行动-观察循环
# 学习计划 Day 2/3 —— 手写最小可用的 ReAct agent
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# ===== 1. 工具箱：两个工具 =====
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气和温度",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如：北京"}
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "计算两个数字相加的结果",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "第一个数字"},
                    "b": {"type": "number", "description": "第二个数字"},
                },
                "required": ["a", "b"],
            },
        },
    },
]

# ===== 2. 工具的真实执行：模型只发"请求"，这里才是"手" =====
def get_weather(city):
    weather_map = {"北京": "晴，26°C", "上海": "多云，28°C", "广州": "小雨，30°C", "深圳": "雷阵雨，29°C"}
    return weather_map.get(city, f"{city}：天气数据暂缺")

def add(a, b):
    return a + b

def execute_tool(name, args):
    """根据工具名分发到真实函数"""
    if name == "get_weather":
        return get_weather(**args)
    if name == "add":
        return add(**args)
    return f"未知工具：{name}"

# ===== 3. ReAct 自动循环 =====
def run_agent(question, max_steps=6):
    messages = [
        {"role": "system", "content": "你是一个能使用工具的智能助手。需要信息时调用工具，拿到结果后继续思考，直到可以给出最终回答。"},
        {"role": "user", "content": question},
    ]
    print(f"🤖 用户提问：{question}\n")

    for step in range(1, max_steps + 1):
        print(f"—— 第 {step} 轮思考 ——")
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=messages,
            tools=TOOLS,
        )
        message = response.choices[0].message

        # 没有工具请求 = 模型给出最终回答，循环结束
        if not message.tool_calls:
            print(f"✅ 模型给出最终回答：{message.content}")
            return message.content

        # 有工具请求：执行并回传
        messages.append(message)
        for tool_call in message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            result = execute_tool(name, args)
            print(f"  → 调用 {name}{args} = {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })

    print("⚠️ 达到最大步数，提前结束")
    return None

# ===== 4. 跑一个需要"多步推理"的任务 =====
if __name__ == "__main__":
    run_agent("帮我查一下北京、广州和深圳今天的天气，然后告诉我哪个城市最适合户外跑步，并顺便计算这三个城市温度加起来的总和。")
