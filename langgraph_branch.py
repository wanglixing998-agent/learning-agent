# LangGraph 实战：条件分支（Conditional Edge）
# 学习计划 Day 4 —— 图的灵魂：节点自己决定下一步走哪条路
# 场景：查真实天气 → 有雨推荐室内 / 晴天推荐户外 → 汇合输出
import requests
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# ===== 1. 状态：整张图共享的数据 =====
class State(TypedDict):
    city: str        # 输入
    weather: str     # 节点1写入：天气描述
    has_rain: bool   # 节点1写入：是否下雨（条件判断依据）
    has_storm: bool  # 节点1写入：是否雷暴（新增）
    plan: str        # 节点2/3写入：推荐方案

# ===== 2. 数据源（真实天气 API）=====
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
# 哪些代码算"下雨"（条件判断用）
RAIN_CODES = {51, 53, 55, 61, 63, 65, 71, 73, 75, 80, 81, 82, 95, 96, 99}

# ===== 3. 节点：每个节点是一个函数 =====
def check_weather(state: State) -> dict:
    """节点1：查真实天气，并判断是否下雨"""
    city = state["city"]
    lat, lon = CITY_COORDS[city]
    resp = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current_weather": "true"},
        timeout=15,
    )
    current = resp.json()["current_weather"]
    code = current["weathercode"]
    desc = WEATHER_CODE.get(code, f"代码{code}")
    temp = current["temperature"]
    weather = f"{desc}，{temp}°C"
    has_rain = code in RAIN_CODES
    has_storm = code in {95, 96, 99}  # 雷暴天气代码
    print(f"    [查天气] {city}：{weather}（下雨？{has_rain} 雷暴？{has_storm}）")
    return {"weather": weather, "has_rain": has_rain, "has_storm": has_storm}

def outdoor_plan(state: State) -> dict:
    """分支A：晴天走的节点"""
    print(f"    [户外推荐] 天气好，安排户外活动！")
    return {"plan": f"天气晴好（{state['weather']}），推荐户外活动：公园散步、爬山、骑行、野餐"}

def indoor_plan(state: State) -> dict:
    """分支B：雨天走的节点"""
    print(f"    [室内推荐] 下雨了，改室内活动！")
    return {"plan": f"有雨（{state['weather']}），推荐室内活动：博物馆、商场、茶馆、电影院"}
def storm_plan(state:State)->dict:
    """分支C：雷暴走的节点"""
    print(f"    [暴雨警告] 暴雨，回家！")
    return {"plan": f"暴雨（{state['weather']}），推荐室内活动：回家"}
def summary(state: State) -> dict:
    """汇合节点：两条路都会走到这里"""
    print(f"    [总结] 生成最终建议")
    return {"plan": f"【{state['city']}出行推荐】{state['plan']}"}

# ===== 4. 条件路由函数：决定下一步走哪条边 =====
def route_by_weather(state: State) -> str:
    """返回值 = 下一个要去的节点名（这就是"条件边"）"""
    if state["has_storm"]:
        return "storm_plan"   # 雷暴 → 走雷暴分支（最优先判断！）
    if state["has_rain"]:
        return "indoor_plan"   # 下雨 → 走室内分支
    return "outdoor_plan"      # 晴天 → 走户外分支

# ===== 5. 建图 =====
builder = StateGraph(State)

# 节点
builder.add_node("check_weather", check_weather)
builder.add_node("outdoor_plan", outdoor_plan)
builder.add_node("indoor_plan", indoor_plan)
builder.add_node("storm_plan",storm_plan)
builder.add_node("summary", summary)

# 普通边（顺序）
builder.add_edge(START, "check_weather")

# 条件边：check_weather 之后，由 route_by_weather 决定去哪个节点
builder.add_conditional_edges(
    "check_weather",
    route_by_weather,
    {"outdoor_plan": "outdoor_plan", "indoor_plan": "indoor_plan", "storm_plan": "storm_plan"},  # 路由返回值 → 实际节点
)

# 两个分支都汇合到 summary
builder.add_edge("outdoor_plan", "summary")
builder.add_edge("indoor_plan", "summary")
builder.add_edge("storm_plan","summary")
builder.add_edge("summary", END)

app = builder.compile()

# ===== 6. 运行：两个城市，走不同分支 =====
if __name__ == "__main__":
    for city in ["广州", "成都"]:
        print(f"\n🎯 输入城市：{city}")
        result = app.invoke({"city": city})
        print(f"✅ 结果：{result['plan']}")
