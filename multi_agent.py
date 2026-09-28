# 多 Agent 协作：旅行规划团队
# 学习计划 Day 5 —— 进阶：多个 AI 角色分工协作
# 管线：行程规划师 → 美食顾问 → 安全提醒官（每个 agent 只干一件事）
import os
import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

load_dotenv()
llm = ChatOpenAI(
    model="deepseek-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
)

class State(TypedDict):
    city: str
    days: int
    weather: str
    plan: str       # Agent A 产出：行程
    food: str       # Agent B 产出：美食
    safety: str     # Agent C 产出：安全
    final: str      # 汇总

CITY_COORDS = {
    "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737),
    "广州": (23.1291, 113.2644), "深圳": (22.5431, 114.0579),
    "成都": (30.5728, 104.0668), "杭州": (30.2741, 120.1551),
}
WEATHER_CODE = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 51: "毛毛雨", 61: "小雨", 63: "中雨", 65: "大雨",
    71: "小雪", 80: "阵雨", 81: "阵雨", 95: "雷暴", 96: "雷暴伴冰雹",
}

def check_weather(state: State) -> dict:
    """确定性节点：真实天气"""
    lat, lon = CITY_COORDS[state["city"]]
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current_weather": "true"},
        timeout=15,
    )
    cur = resp.json()["current_weather"]
    desc = WEATHER_CODE.get(cur["weathercode"], f"代码{cur['weathercode']}")
    weather = f"{desc}，{cur['temperature']}°C"
    print(f"    [查数据] {state['city']}：{weather}")
    return {"weather": weather}

def agent_planner(state: State) -> dict:
    """🧑‍💼 Agent A：行程规划师（角色隔离：只负责行程）"""
    print(f"    [规划师] 正在安排{state['days']}天行程……")
    prompt = (
        f"你是资深旅行规划师。为【{state['city']}】规划{state['days']}日游行程。\n"
        f"当前天气：{state['weather']}\n"
        "要求：只输出每天的行程安排（上午/下午/晚上），不要写美食和安全事项。"
    )
    plan = llm.invoke(prompt).content.strip()
    return {"plan": plan}

def agent_foodie(state: State) -> dict:
    """🍜 Agent B：美食顾问（只负责美食，输入依赖规划师的产出）"""
    print(f"    [美食顾问] 根据行程推荐当地美食……")
    prompt = (
        f"你是【{state['city']}】当地美食顾问。\n"
        f"游客的行程安排如下：\n{state['plan']}\n"
        "要求：推荐每天对应的特色美食（哪一餐吃什么），只输出美食推荐，不要写行程和安全。"
    )
    food = llm.invoke(prompt).content.strip()
    return {"food": food}

def agent_safety(state: State) -> dict:
    """🛡️ Agent C：安全提醒官（只负责安全）"""
    print(f"    [安全官] 根据天气评估风险……")
    prompt = (
        f"你是旅行安全顾问。\n"
        f"目的地：【{state['city']}】，天气：{state['weather']}\n"
        "要求：只输出出行安全注意事项（穿衣、防雨、防晒等），不要写行程和美食。"
    )
    safety = llm.invoke(prompt).content.strip()
    return {"safety": safety}

def merge(state: State) -> dict:
    """汇总：把三个 agent 的成果拼成完整方案"""
    print(f"    [汇总] 拼装团队成果……")
    final = (
        f"【行程】\n{state['plan']}\n\n"
        f"【美食】\n{state['food']}\n\n"
        f"【安全】\n{state['safety']}"
    )
    return {"final": final}

# ===== 建图：管线式协作 =====
builder = StateGraph(State)
builder.add_node("check_weather", check_weather)
builder.add_node("agent_planner", agent_planner)
builder.add_node("agent_foodie", agent_foodie)
builder.add_node("agent_safety", agent_safety)
builder.add_node("merge", merge)

builder.add_edge(START, "check_weather")
builder.add_edge("check_weather", "agent_planner")
builder.add_edge("agent_planner", "agent_foodie")   # 美食依赖行程 → 必须在前者之后
builder.add_edge("agent_foodie", "agent_safety")
builder.add_edge("agent_safety", "merge")
builder.add_edge("merge", END)

app = builder.compile()

if __name__ == "__main__":
    result = app.invoke({"city": "成都", "days": 2})
    print("\n" + "=" * 40)
    print("🏆 旅行规划团队完整方案（成都 2 日）：")
    print(result["final"])
