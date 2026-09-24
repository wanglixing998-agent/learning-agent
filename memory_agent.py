# 带记忆的 ReAct Agent：跨对话记住上下文
# 学习计划 Day 2/3 —— 记忆机制（短期记忆）
import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# ===== 1. 工具箱 =====
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
            "name": "get_time",
            "description": "查询指定城市的当前时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如：北京"}
                },
                "required": ["city"],
            },
        },
    },
]

# ===== 2. 工具执行 =====
def get_weather(city):
    weather_map = {"北京": "晴，26°C", "上海": "多云，28°C", "广州": "小雨，30°C", "深圳": "雷阵雨，29°C"}
    return weather_map.get(city, f"{city}：天气数据暂缺")

def get_time(city):
    time_map = {"北京": "14:30", "上海": "14:30", "广州": "14:30"}
    return time_map.get(city, f"{city}：时间数据暂缺")

def execute_tool(name, args):
    if name == "get_weather":
        return get_weather(**args)
    if name == "get_time":
        return get_time(**args)
    return f"未知工具：{name}"

# ===== 3. 带记忆的 Agent =====
class MemoryAgent:
    """把 messages 保存在对象里，多次提问共享同一份记忆"""

    def __init__(self, system_prompt=None):
        # 记忆的核心：messages 列表在对象生命周期内持续存在
        self.messages = [
            {"role": "system", "content": system_prompt or "你是一个能使用工具的智能助手。需要信息时调用工具，直到可以给出最终回答。"}
        ]

    def chat(self, question, max_steps=6):
        """提问一次，用共享的记忆完成任务"""
        self.messages.append({"role": "user", "content": question})
        print(f"🤖 用户：{question}")

        for step in range(1, max_steps + 1):
            response = client.chat.completions.create(
                model="deepseek-flash",
                messages=self.messages,
                tools=TOOLS,
            )
            message = response.choices[0].message

            if not message.tool_calls:
                print(f"💬 助手：{message.content}\n")
                # 记住这次回答（重要：最终回答也进记忆）
                self.messages.append(message)
                return message.content

            self.messages.append(message)
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                result = execute_tool(name, args)
                print(f"  → 调用 {name}{args} = {result}")
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(result),
                })

        print("⚠️ 达到最大步数")
        return None

# ===== 4. 演示：两次提问，第二次用到了第一次的记忆 =====
if __name__ == "__main__":
    agent = MemoryAgent()

    # 第一次提问：查北京天气
    agent.chat("北京今天天气怎么样？")

    # 第二次提问：完全不提"北京"，看它是否记得
    agent.chat("那上海的天气和北京比怎么样？")
    agent.chat("我第一个问的是哪个城市？它的温度是多少？")
