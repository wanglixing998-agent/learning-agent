# 智能旅行规划 Agent：LangGraph 完整项目
# 学习计划 Day 4 —— 阶段 4 项目实战开端
# 一张图跑通：真实天气+预报 → LLM 判断 → 生成完整行程
import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

load_dotenv()

# ===== 1. 大模型 =====
llm = ChatOpenAI(
    model="deepseek-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
)

# ===== 2. 状态 =====
class State(TypedDict):
    city: str          # 输入：城市
    days: int          # 输入：天数
    weather: str       # 节点1：当前天气
    forecast: str      # 节点1：未来几天预报
    trip_style: str    # 节点2：LLM 判断的出行类型（outdoor/indoor/storm）
    style_note: str    # 分支节点：风格说明（必须声明，否则节点返回值会被丢弃）
    itinerary: str     # 节点4：最终行程

# ===== 3. 数据源 =====
CITY_COORDS = {
    "北京": (39.9042, 116.4074),
    "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644),
    "深圳": (22.5431, 114.0579),
    "成都": (30.5728, 104.0668),
    "杭州": (30.2741, 120.1551),
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

# ===== 4. 节点1（确定性）：查当前天气 + 未来预报 =====
def check_weather(state: State) -> dict:
    """同时查当前天气和未来几天预报（旅行需要看趋势）"""
    city = state["city"]
    lat, lon = CITY_COORDS[city]
    # 当前天气
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current_weather": "true"},
        timeout=15,
    )
    current = resp.json()["current_weather"]
    desc = WEATHER_CODE.get(current["weathercode"], f"代码{current['weathercode']}")
    weather = f"{desc}，{current['temperature']}°C"

    # 未来几天预报
    resp2 = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat, "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": state["days"],
            "timezone": "Asia/Shanghai",
        },
        timeout=15,
    )
    daily = resp2.json()["daily"]
    lines = []
    for i, day in enumerate(daily["time"]):
        d = WEATHER_CODE.get(daily["weather_code"][i], f"代码{daily['weather_code'][i]}")
        lines.append(
            f"{day}:{d},最高{daily['temperature_2m_max'][i]}°C/最低{daily['temperature_2m_min'][i]}°C,降水{daily['precipitation_probability_max'][i]}%"
        )
    forecast = " | ".join(lines)
    print(f"    [查数据] {city}：当前{weather} | 未来{state['days']}天：{forecast}")
    return {"weather": weather, "forecast": forecast}

# ===== 5. 节点2（智能）：LLM 判断天气类型 =====
def parse_style(decision: str) -> str:
    """纯函数：LLM 输出 → 出行类型（可单元测试）"""
    d = decision.strip().lower()
    if "storm" in d:
        return "storm"
    if "outdoor" in d:
        return "outdoor"
    return "indoor"

def judge_weather(state: State) -> str:
    """LLM Router：判断未来几天整体适合哪种旅行风格"""
    prompt = (
        f"未来{state['days']}天天气：{state['forecast']}\n"
        "判断这几天整体适合哪种旅行风格，只回答一个词：\n"
        "- 有雷暴/极端天气 → storm\n"
        "- 整体晴好 → outdoor\n"
        "- 有雨/阴冷 → indoor\n"
        "只输出一个词。"
    )
    decision = llm.invoke(prompt).content.strip().lower()
    style = parse_style(decision)
    print(f"    [LLM 判断] 旅行风格 → {style}")
    return {"trip_style": style}

# ===== 6. 分支节点（确定性）：定活动基调 =====
def outdoor_style(state: State) -> dict:
    return {"trip_style": state["trip_style"], "style_note": "天气晴好，主打户外自然风光"}

def indoor_style(state: State) -> dict:
    return {"trip_style": state["trip_style"], "style_note": "有雨偏凉，主打室内文化体验"}

def storm_style(state: State) -> dict:
    return {"trip_style": state["trip_style"], "style_note": "有雷暴风险，安全第一，室内为主"}

# ===== 7. 节点3（智能）：LLM 生成完整行程 =====
def build_itinerary(state: State) -> dict:
    """结合天气+预报+风格，生成完整 N 天行程"""
    prompt = (
        f"为【{state['city']}】规划一份{state['days']}日游行程。\n"
        f"当前天气：{state['weather']}\n"
        f"未来预报：{state['forecast']}\n"
        f"出行风格：{state['style_note']}\n"
        "请输出：\n"
        "1) 每天上午/下午/晚上安排（结合真实景点，注意天气调整）\n"
        "2) 穿衣建议\n"
        "3) 注意事项（如带伞、防晒）\n"
        "用简洁列表，总长度控制在 400 字内。"
    )
    itinerary = llm.invoke(prompt).content.strip()
    print(f"    [LLM 生成] 完成 {state['days']} 日行程")
    return {"itinerary": itinerary}

# ===== 8. 建图 =====
builder = StateGraph(State)
builder.add_node("check_weather", check_weather)
builder.add_node("judge_weather", judge_weather)
builder.add_node("outdoor_style", outdoor_style)
builder.add_node("indoor_style", indoor_style)
builder.add_node("storm_style", storm_style)
builder.add_node("build_itinerary", build_itinerary)

builder.add_edge(START, "check_weather")
builder.add_edge("check_weather", "judge_weather")

# 条件边：LLM 判断 → 三种风格分支
def route_by_style(state: State) -> str:
    return state["trip_style"] + "_style"

builder.add_conditional_edges(
    "judge_weather",
    route_by_style,
    {"outdoor_style": "outdoor_style", "indoor_style": "indoor_style", "storm_style": "storm_style"},
)

builder.add_edge("outdoor_style", "build_itinerary")
builder.add_edge("indoor_style", "build_itinerary")
builder.add_edge("storm_style", "build_itinerary")
builder.add_edge("build_itinerary", END)

app = builder.compile()

# ===== 9. 运行 =====
if __name__ == "__main__":
    result = app.invoke({"city": "广州", "days": 2})
    print("\n" + "=" * 40)
    print("📋 广州 2 日游行程：")
    print(result["itinerary"])
