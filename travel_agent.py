# 旅行规划助手：你的第一个完整 Agent 应用
# 学习计划 Day 3 —— 整合全部能力（规划 + 真实天气 + 未来预报 + 时间）
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

# ===== 1. 工具箱：4 个工具 =====
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前实时天气和温度",
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
            "name": "get_forecast",
            "description": "查询指定城市未来N天的天气预报（含最高/最低温度和降水概率）",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如：成都"},
                    "days": {"type": "integer", "description": "预报天数，如 3"},
                },
                "required": ["city", "days"],
            },
        },
    },
]

# ===== 2. 真实数据源 =====
CITY_COORDS = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "成都": (30.5728, 104.0668),
    "杭州": (30.2741, 120.1551),
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

# ===== 3. 工具执行（真实 API）=====
def get_weather(city):
    """实时天气"""
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
        desc = WEATHER_CODE.get(current["weathercode"], f"代码{current['weathercode']}")
        return f"{city}：{desc}，{current['temperature']}°C，风速{current['windspeed']}km/h"
    except Exception as e:
        return f"{city}：天气查询失败（{e}）"

def get_time(city):
    """真实时间（中国统一北京时间）"""
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

def get_forecast(city, days):
    """未来 N 天预报"""
    if city not in CITY_COORDS:
        return f"{city}：暂不支持该城市"
    lat, lon = CITY_COORDS[city]
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "forecast_days": days,
                "timezone": "Asia/Shanghai",
            },
            timeout=15,
        )
        daily = resp.json()["daily"]
        lines = []
        for i, day in enumerate(daily["time"]):
            desc = WEATHER_CODE.get(daily["weather_code"][i], f"代码{daily['weather_code'][i]}")
            rain = daily["precipitation_probability_max"][i]
            lines.append(
                f"{day}：{desc}，最高{daily['temperature_2m_max'][i]}°C，最低{daily['temperature_2m_min'][i]}°C，降水概率{rain}%"
            )
        return f"{city}未来{days}天预报：\n" + "\n".join(lines)
    except Exception as e:
        return f"{city}：预报查询失败（{e}）"

def execute_tool(name, args):
    if name == "get_weather":
        return get_weather(**args)
    if name == "get_time":
        return get_time(**args)
    if name == "get_forecast":
        return get_forecast(**args)
    return f"未知工具：{name}"

# ===== 4. 规划-执行循环（复用 Plan-and-Execute）=====
class TravelAgent:

    def __init__(self):
        self.messages = [
            {"role": "system", "content": "你是旅行规划助手。面对旅行任务，先规划再执行：查天气、查预报、查时间，然后给出完整建议。"}
        ]

    def plan(self, task):
        print("=" * 50)
        print("📋 规划：拆解旅行任务")
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=[
                {"role": "system", "content": "你是旅行规划器。把旅行任务拆解成执行步骤，用 1. 2. 3. 列出，不要执行。"},
                {"role": "user", "content": task},
            ],
            extra_body={"enable_thinking": False},
        )
        plan = response.choices[0].message.content
        print(plan)
        return plan

    def execute(self, task, plan):
        print("=" * 50)
        print("⚙️ 执行：按计划调用工具")
        self.messages.append({"role": "user", "content": task})
        self.messages.append({
            "role": "assistant",
            "content": f"我的执行计划是：\n{plan}\n现在开始逐步执行。",
            "reasoning_content": "",
        })

        for step in range(1, 8):
            response = client.chat.completions.create(
                model="deepseek-flash",
                messages=self.messages,
                tools=TOOLS,
                extra_body={"enable_thinking": False},
            )
            message = response.choices[0].message

            if not message.tool_calls:
                print(f"✅ 完成：{message.content}")
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
        plan = self.plan(task)
        return self.execute(task, plan)

# ===== 5. 演示：一次完整的旅行规划 =====
if __name__ == "__main__":
    agent = TravelAgent()
    agent.run(
        "帮我规划一次成都 3 日游：查一下未来 3 天的天气，"
        "根据天气告诉我每天适合玩什么、穿什么，最后给出一个简短的行程安排。"
    )
