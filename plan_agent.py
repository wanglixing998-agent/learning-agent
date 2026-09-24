# Plan-and-Execute Agent：先规划，再执行
# 学习计划 Day 3 —— 多步任务规划
import json
import os
import requests
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

# ===== 2. 工具执行 =====
# ---- 真实天气 API（Open-Meteo，免费无需 key）----
CITY_COORDS = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "成都": (30.5728, 104.0668),
}

# WMO 国际天气代码 → 中文
WEATHER_CODE = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "阵雨", 81: "阵雨", 82: "强阵雨",
    95: "雷暴", 96: "雷暴伴冰雹", 99: "雷暴伴冰雹",
}

def get_weather(city):
    """真实天气：调用 Open-Meteo API 获取城市实时天气"""
    if city not in CITY_COORDS:
        return f"{city}：暂不支持该城市"
    lat, lon = CITY_COORDS[city]
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current_weather": "true"},
            timeout=15,
        )
        current = resp.json()["current_weather"]
        temp = current["temperature"]
        desc = WEATHER_CODE.get(current["weathercode"], f"代码{current['weathercode']}")
        wind = current["windspeed"]
        return f"{city}：{desc}，{temp}°C，风速{wind}km/h"
    except Exception as e:
        return f"{city}：天气查询失败（{e}）"

def get_time(city):
    """真实时间：调用 timeapi.io 获取北京时间（中国统一时区 Asia/Shanghai）"""
    try:
        resp = requests.get(
            "https://timeapi.io/api/time/current/zone",
            params={"timeZone": "Asia/Shanghai"},
            timeout=15,
        )
        data = resp.json()
        return f"{city}：{data['dateTime'][:16]}（北京时间）"
    except Exception as e:
        return f"{city}：时间查询失败（{e}）"

def add(a, b):
    return a + b

def execute_tool(name, args):
    if name == "get_weather":
        return get_weather(**args)
    if name == "get_time":
        return get_time(**args)
    if name == "add":
        return add(**args)
    return f"未知工具：{name}"

# ===== 3. Plan-and-Execute Agent =====
class PlanExecuteAgent:

    def __init__(self):
        self.messages = [
            {"role": "system", "content": "你是一个能使用工具的智能助手，擅长先规划再执行。"}
        ]

    def plan(self, task):
        """第一步：只做规划，不调用工具"""
        print("=" * 50)
        print("📋 规划阶段：模型先拆解任务")
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=[
                {"role": "system", "content": "你是任务规划器。请把任务拆解成清晰的执行步骤，用 1. 2. 3. 列出，不要执行。"},
                {"role": "user", "content": task},
            ],
            extra_body={"enable_thinking": False},  # 关闭思考模式（学习阶段不需要）
        )
        plan = response.choices[0].message.content
        print(plan)
        return plan

    def execute(self, task, plan):
        """第二步：带着计划进入 ReAct 循环执行"""
        print("=" * 50)
        print("⚙️ 执行阶段：按计划逐步调用工具")
        self.messages.append({"role": "user", "content": task})
        self.messages.append({
            "role": "assistant",
            "content": f"我的执行计划是：\n{plan}\n现在开始逐步执行。",
            "reasoning_content": "",  # DeepSeek 思考模式要求回传该字段
        })

        for step in range(1, 8):
            response = client.chat.completions.create(
                model="deepseek-flash",
                messages=self.messages,
                tools=TOOLS,
                extra_body={"enable_thinking": False},  # 关闭思考模式
            )
            message = response.choices[0].message

            if not message.tool_calls:
                print(f"✅ 执行完成：{message.content}")
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

    def run(self, task):
        """完整流程：规划 → 执行"""
        plan = self.plan(task)
        return self.execute(task, plan)

# ===== 4. 演示：一个需要多步骤的复杂任务 =====
if __name__ == "__main__":
    agent = PlanExecuteAgent()
    agent.run("帮我查一下成都今天的天气，再查一下北京的天气对比，推荐一个更适合旅游的城市。")

