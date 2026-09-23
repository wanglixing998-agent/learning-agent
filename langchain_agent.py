# LangChain Agent：用框架重写手写版
# 学习计划 Day 3 —— 阶段 3 框架入门
# 对比 react_agent.py：循环、消息管理、工具解析全由框架接管
import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent

load_dotenv()

# ===== 1. 大模型（DeepSeek，OpenAI 兼容）=====
llm = ChatOpenAI(
    model="deepseek-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
)

# ===== 2. 工具：用 @tool 装饰器，框架自动生成工具声明 =====
# 手写版：要手动写 TOOLS 的 JSON（name/description/parameters）
# LangChain：一个 @tool + 函数签名就搞定
CITY_COORDS = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "成都": (30.5728, 104.0668),
}

WEATHER_CODE = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "毛毛雨", 53: "毛毛雨", 55: "毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 73: "中雪", 75: "大雪",
    80: "阵雨", 81: "阵雨", 82: "强阵雨",
    95: "雷暴", 96: "雷暴伴冰雹", 99: "雷暴伴冰雹",
}

@tool
def get_weather(city: str) -> str:
    """查询指定城市的当前实时天气和温度"""
    if city not in CITY_COORDS:
        return f"{city}：暂不支持该城市"
    lat, lon = CITY_COORDS[city]
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current_weather": "true"},
        timeout=15,
    )
    current = resp.json()["current_weather"]
    desc = WEATHER_CODE.get(current["weathercode"], f"代码{current['weathercode']}")
    return f"{city}：{desc}，{current['temperature']}°C"

@tool
def get_time(city: str) -> str:
    """查询指定城市的当前时间"""
    resp = requests.get(
        "https://timeapi.io/api/time/current/zone",
        params={"timeZone": "Asia/Shanghai"},
        timeout=15,
    )
    return f"{city}：{resp.json()['dateTime'][:16]}（北京时间）"

@tool
def get_forecast(city: str, days: int) -> str:
    """查询指定城市未来N天的天气预报（含最高/最低温度和降水概率）"""
    if city not in CITY_COORDS:
        return f"{city}：暂不支持该城市"
    lat, lon = CITY_COORDS[city]
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
        lines.append(
            f"{day}：{desc}，最高{daily['temperature_2m_max'][i]}°C，最低{daily['temperature_2m_min'][i]}°C，降水概率{daily['precipitation_probability_max'][i]}%"
        )
    return f"{city}未来{days}天预报：\n" + "\n".join(lines)

tools = [get_weather, get_time, get_forecast]

# ===== 3. Agent：一行创建，框架管理整个 ReAct 循环 =====
# 手写版：自己写 for 循环、自己管理 messages、自己解析 tool_calls
# LangChain：create_agent 一个函数搞定（内部就是 LangGraph 图）
agent = create_agent(
    llm,
    tools,
    system_prompt="你是一个能使用工具的智能助手，擅长先规划再执行。",
)

# ===== 4. 运行 =====
if __name__ == "__main__":
    result = agent.invoke({"messages": [{"role": "user", "content": "帮我查一下北京和成都今天天气，推荐一个更适合旅游的城市。"}]})
    print("\n" + "=" * 30)
    print("最终回答：")
    print(result["messages"][-1].content)
