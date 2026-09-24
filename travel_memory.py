# 记忆与持久化：SQLite 长期记忆 + 用户偏好
# 学习计划 Day 4 —— agent 的"记忆"= 数据库
# 每次规划结果存库，下次能查历史；记住用户偏好，规划时自动参考
import os
import sqlite3
from datetime import datetime
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

# ============================================================
# 第一部分：SQLite 数据库（长期记忆）
# ============================================================
DB_PATH = r"D:\workspace\learning-agent\travel_memory.db"

def init_db():
    """建表：第一次运行创建数据库文件"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # 行程记录表
    cur.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL,
            days INTEGER,
            style TEXT,
            itinerary TEXT,
            created_at TEXT
        )
    """)
    # 用户偏好表（只存一条，id 固定为 1）
    cur.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            content TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("📦 数据库就绪：travel_memory.db")

def save_plan(city: str, days: int, style: str, itinerary: str):
    """把一次行程存进数据库"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO plans (city, days, style, itinerary, created_at) VALUES (?, ?, ?, ?, ?)",
        (city, days, style, itinerary, datetime.now().strftime("%Y-%m-%d %H:%M")),
    )
    conn.commit()
    conn.close()
    print(f"💾 已存入历史记录：{city} {days}日游")

def get_history(limit: int = 5):
    """查询最近的行程历史"""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT city, days, style, created_at FROM plans ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return rows

def set_preference(text: str):
    """保存用户偏好（覆盖旧的）"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO preferences (id, content) VALUES (1, ?)",
        (text,),
    )
    conn.commit()
    conn.close()
    print(f"🧠 记住了你的偏好：{text}")

def get_preference():
    """读取用户偏好（没有则返回 None）"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT content FROM preferences WHERE id = 1").fetchone()
    conn.close()
    return row[0] if row else None

# ============================================================
# 第二部分：LangGraph 图（复用旅行规划，加上偏好和存储）
# ============================================================
class State(TypedDict):
    city: str
    days: int
    weather: str
    forecast: str
    trip_style: str
    style_note: str
    preference: str   # 新增：用户偏好
    itinerary: str

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

def check_weather(state: State) -> dict:
    city = state["city"]
    lat, lon = CITY_COORDS[city]
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current_weather": "true"},
        timeout=15,
    )
    current = resp.json()["current_weather"]
    desc = WEATHER_CODE.get(current["weathercode"], f"代码{current['weathercode']}")
    weather = f"{desc}，{current['temperature']}°C"
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
        lines.append(f"{day}:{d},最高{daily['temperature_2m_max'][i]}°C/最低{daily['temperature_2m_min'][i]}°C,降水{daily['precipitation_probability_max'][i]}%")
    print(f"    [查数据] {city}：当前{weather} | 未来{state['days']}天预报已获取")
    return {"weather": weather, "forecast": " | ".join(lines)}

def judge_weather(state: State) -> str:
    prompt = (
        f"未来{state['days']}天天气：{state['forecast']}\n"
        "判断整体旅行风格，只回答一个词：storm（雷暴）/ outdoor（晴好）/ indoor（有雨）"
    )
    decision = llm.invoke(prompt).content.strip().lower()
    if "storm" in decision:
        style = "storm"
    elif "outdoor" in decision:
        style = "outdoor"
    else:
        style = "indoor"
    print(f"    [LLM 判断] 旅行风格 → {style}")
    return {"trip_style": style}

def outdoor_style(state: State) -> dict:
    return {"style_note": "天气晴好，主打户外自然风光"}
def indoor_style(state: State) -> dict:
    return {"style_note": "有雨偏凉，主打室内文化体验"}
def storm_style(state: State) -> dict:
    return {"style_note": "有雷暴风险，安全第一，室内为主"}

def load_preference(state: State) -> dict:
    """新增节点：规划前读取用户偏好"""
    pref = get_preference()
    print(f"    [记忆] 读取用户偏好 → {pref or '（无偏好）'}")
    return {"preference": pref or ""}

def build_itinerary(state: State) -> dict:
    pref_part = f"\n用户偏好：{state['preference']}（规划时务必满足）" if state["preference"] else ""
    prompt = (
        f"为【{state['city']}】规划一份{state['days']}日游行程。\n"
        f"当前天气：{state['weather']}\n"
        f"未来预报：{state['forecast']}\n"
        f"出行风格：{state['style_note']}"
        f"{pref_part}\n"
        "请输出：1) 每天上午/下午/晚上安排（结合真实景点） 2) 穿衣建议 3) 注意事项。用简洁列表，400字内。"
    )
    itinerary = llm.invoke(prompt).content.strip()
    print(f"    [LLM 生成] 完成 {state['days']} 日行程")
    return {"itinerary": itinerary}

# 建图
builder = StateGraph(State)
builder.add_node("check_weather", check_weather)
builder.add_node("load_preference", load_preference)
builder.add_node("judge_weather", judge_weather)
builder.add_node("outdoor_style", outdoor_style)
builder.add_node("indoor_style", indoor_style)
builder.add_node("storm_style", storm_style)
builder.add_node("build_itinerary", build_itinerary)

builder.add_edge(START, "check_weather")
builder.add_edge("check_weather", "load_preference")
builder.add_edge("load_preference", "judge_weather")

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

# ============================================================
# 第三部分：演示 —— 记忆的完整流程
# ============================================================
def plan_trip(city: str, days: int):
    """跑一次规划并自动存库"""
    result = app.invoke({"city": city, "days": days})
    print(f"\n📋 {city} {days}日游：")
    print(result["itinerary"])
    print()
    # 规划完自动存入数据库（长期记忆）
    save_plan(city, days, result["trip_style"], result["itinerary"])
    return result

if __name__ == "__main__":
    init_db()

    # 1. 记住用户偏好（模拟用户设置）
    set_preference("用户喜欢美食和轻松节奏：每天安排一顿当地特色美食，景点不要排太满，留出休息时间。")

    # 2. 第一次规划（偏好会生效）
    plan_trip("广州", 2)

    # 3. 第二次规划（换城市，同样记住）
    plan_trip("成都", 3)

    # 4. 查询历史：agent 记得之前规划过什么
    print("=" * 40)
    print("🗂️ 历史记录（agent 的长期记忆）：")
    for row in get_history():
        print(f"  - {row[3]} | {row[0]} {row[1]}日游 | 风格:{row[2]}")
