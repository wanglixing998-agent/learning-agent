# LangGraph 入门：Agent 是一张图
# 学习计划 Day 3/4 —— 节点（Node）+ 边（Edge）= 图
# 演示1：看 create_agent 内部结构
# 演示2：手写一张自己的图（带条件分支）
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

load_dotenv()

llm = ChatOpenAI(
    model="deepseek-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
)

print("=" * 60)
print("演示1：create_agent 内部就是一张图")
print("=" * 60)

@tool
def add(a: float, b: float) -> float:
    """计算两个数字相加的结果"""
    return a + b

agent = create_agent(llm, [add], system_prompt="你是助手。")
# get_graph() 把图结构导出来（节点和边）
graph_json = agent.get_graph().to_json()
for n in graph_json.get("nodes", []):
    print(f"  📍 节点: {n.get('id')}")
for e in graph_json.get("edges", []):
    print(f"  🔗 边: {e.get('source')} → {e.get('target')}" + (f"  条件: {e.get('metadata', {}).get('label', '')}" if e.get('metadata') else ""))
print()

print("=" * 60)
print("演示2：手写一张图——天气旅行小助手")
print("=" * 60)

# ---- 1. 定义"状态"：整张图共享的数据结构 ----
class State(TypedDict):
    city: str      # 输入：城市
    weather: str   # 节点1的输出
    suggestion: str  # 节点2的输出

# ---- 2. 定义"节点"：每个节点是一个函数，读状态、写状态 ----
def check_weather(state: State) -> dict:
    """节点1：查天气（模拟）"""
    print(f"    [节点1] 查询 {state['city']} 天气...")
    # 实际可换成真实 API
    return {"weather": "晴，26°C"}

def decide(state: State) -> dict:
    """节点2：根据天气给建议"""
    print(f"    [节点2] 根据天气分析：{state['weather']}")
    if "雨" in state["weather"]:
        return {"suggestion": "下雨了，建议带伞，玩室内景点"}
    return {"suggestion": "天气好，适合户外活动！"}

def summary(state: State) -> dict:
    """节点3：汇总输出"""
    print(f"    [节点3] 生成最终报告")
    return {"suggestion": f"【{state['city']}出行建议】天气：{state['weather']}。{state['suggestion']}"}

# ---- 3. 建图：把节点和边组装起来 ----
builder = StateGraph(State)

# 加节点
builder.add_node("check_weather", check_weather)
builder.add_node("decide", decide)
builder.add_node("summary", summary)

# 加边：起点 → 节点1 → 节点2 → 节点3 → 终点（顺序执行）
builder.add_edge(START, "check_weather")
builder.add_edge("check_weather", "decide")
builder.add_edge("decide", "summary")
builder.add_edge("summary", END)

# ---- 4. 编译：图变成可执行对象 ----
app = builder.compile()

# ---- 5. 运行：给状态一个输入，水流过整张图 ----
print("\n  运行流程：")
result = app.invoke({"city": "成都"})
print(f"\n  最终输出：{result['suggestion']}")
