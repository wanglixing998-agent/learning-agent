# LangGraph + 大模型：LLM Router（智能节点）
# 学习计划 Day 4 —— 让大模型决定图走哪条边
# 混合架构：确定性节点（查天气）+ 智能节点（LLM 判断/生成）
import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

load_dotenv()

# ===== 1. 大模型（智能节点的"大脑"）=====
llm = ChatOpenAI(
    model="deepseek-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
)

# ===== 2. 状态 =====
class State(TypedDict):
    city: str         # 输入
    weather_text: str # 节点1写入：天气原始描述
    plan: str         # 智能节点写入：最终建议

# ===== 3. 确定性节点：查真实天气（死代码，但数据真实）=====
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

def check_weather(state: State) -> dict:
    """节点1（确定性）：查真实天气，输出描述文本"""
    city = state["city"]
    lat, lon = CITY_COORDS[city]
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current_weather": "true"},
        timeout=15,
    )
    current = resp.json()["current_weather"]
    desc = WEATHER_CODE.get(current["weathercode"], f"代码{current['weathercode']}")
    weather_text = f"{desc}，{current['temperature']}°C，风速{current['windspeed']}km/h"
    print(f"    [确定性节点] 查天气：{city} → {weather_text}")
    return {"weather_text": weather_text}

# ===== 4. 智能节点1：LLM Router（让大模型决定走哪条边）=====
def llm_router(state: State) -> str:
    """条件边：把天气交给大模型，让它判断适合哪种出行"""
    prompt = (
        f"当前天气：{state['weather_text']}。\n"
        "请判断这种天气更适合哪种出行方式。只回答一个词：\n"
        "- 如果适合户外活动（如晴天、多云），回答 outdoor\n"
        "- 如果适合室内活动（如下雨、雷暴、恶劣天气），回答 indoor\n"
        "不要输出其他内容。"
    )
    decision = llm.invoke(prompt).content.strip().lower()
    print(f"    [智能节点] LLM 判断天气 → {decision}")
    if "outdoor" in decision:
        return "outdoor_plan"
    return "indoor_plan"

# ===== 5. 确定性节点：两个分支方案 =====
def outdoor_plan(state: State) -> dict:
    print(f"    [分支] 户外方案")
    return {"plan": f"天气：{state['weather_text']}。适合户外活动：公园、爬山、骑行。"}

def indoor_plan(state: State) -> dict:
    print(f"    [分支] 室内方案")
    return {"plan": f"天气：{state['weather_text']}。适合室内活动：博物馆、茶馆、商场。"}

# ===== 6. 智能节点2：LLM 生成最终建议 =====
def llm_summary(state: State) -> dict:
    """汇合节点：让大模型把方案加工成完整的出行建议"""
    prompt = (
        f"城市：{state['city']}。\n"
        f"当前天气：{state['weather_text']}。\n"
        f"初步方案：{state['plan']}。\n"
        "请生成一段简短（50字以内）、友好的出行建议，包含穿衣提示。"
    )
    final = llm.invoke(prompt).content.strip()
    print(f"    [智能节点] LLM 生成最终建议")
    return {"plan": final}

# ===== 7. 建图 =====
builder = StateGraph(State)
builder.add_node("check_weather", check_weather)
builder.add_node("outdoor_plan", outdoor_plan)
builder.add_node("indoor_plan", indoor_plan)
builder.add_node("llm_summary", llm_summary)

builder.add_edge(START, "check_weather")

# 条件边：路由函数是 LLM（智能判断）
builder.add_conditional_edges(
    "check_weather",
    llm_router,
    {"outdoor_plan": "outdoor_plan", "indoor_plan": "indoor_plan"},
)

builder.add_edge("outdoor_plan", "llm_summary")
builder.add_edge("indoor_plan", "llm_summary")
builder.add_edge("llm_summary", END)

app = builder.compile()

# ===== 8. 运行 =====
if __name__ == "__main__":
    for city in ["广州", "成都"]:
        print(f"\n🎯 输入城市：{city}")
        result = app.invoke({"city": city})
        print(f"✅ 最终建议：{result['plan']}")
