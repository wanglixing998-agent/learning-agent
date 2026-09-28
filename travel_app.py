# 交互式旅行规划助手：把 agent 变成"产品"
# 学习计划 Day 5 —— 阶段 4 收官：命令行交互应用
# 核心：复用 travel_memory 的图和数据库，加上用户交互层
import sys
sys.path.insert(0, r"D:\workspace\learning-agent")

from travel_memory import app, save_plan, get_history, CITY_COORDS

# ============================================================
# 输入净化：用户输入可能混入"看不见的字符"（BOM、零宽空格等）
# 从网页复制、跨系统粘贴都会带——产品必须先清理再处理
# ============================================================
def clean_text(text: str) -> str:
    """去掉输入中的不可见字符，再去掉首尾空格"""
    for ch in ("\ufeff", "\u200b", "\u200c", "\u200d"):
        text = text.replace(ch, "")
    return text.strip()

# ============================================================
# 核心业务：跑图 + 自动存库（复用已写好的代码）
# ============================================================
def plan_trip(city: str, days: int):
    """输入城市和天数 → 跑完整张图 → 返回行程结果"""
    print(f"\n⏳ 正在为【{city} {days}日游】规划……")
    result = app.invoke({"city": city, "days": days})
    print("\n📋 行程方案：")
    print(result["itinerary"])
    # 自动存入长期记忆
    save_plan(city, days, result["trip_style"], result["itinerary"])
    print()
    return result

# ============================================================
# 交互主循环：产品要有"输入 → 校验 → 处理 → 反馈"
# ============================================================
SUPPORTED_CITIES = "、".join(CITY_COORDS.keys())

def main():
    print("=" * 50)
    print("🌏 智能旅行规划助手（命令行版）")
    print("=" * 50)
    print(f"支持城市：{SUPPORTED_CITIES}")
    print("用法：输入「城市 天数」，如「成都 3」")
    print("输入 quit 退出\n")

    while True:
        # ---- 1. 输入（先净化：去掉隐形字符）----
        cmd = clean_text(input("👉 你想去哪里？> "))

        # ---- 2. 退出判断（产品必须能随时退出）----
        if cmd.lower() in ("quit", "q", "exit", "退出"):
            print("👋 再见！旅途愉快！")
            break

        # ---- 3. 解析输入：拆成「城市 天数」两个词 ----
        parts = cmd.split()
        if len(parts) != 2:
            print("❌ 格式不对！请输入「城市 天数」，例如：成都 3\n")
            continue

        city, days_str = parts
        city = clean_text(city)   # 城市名也净化（可能有隐形字符）

        # ---- 4. 校验城市（防呆：输错不崩溃，给提示）----
        if city not in CITY_COORDS:
            print(f"❌ 暂不支持「{city}」，支持：{SUPPORTED_CITIES}\n")
            continue

        # ---- 5. 校验天数（必须是 1-7 的整数）----
        try:
            days = int(days_str)
        except ValueError:
            print("❌ 天数必须是数字！例如：成都 3\n")
            continue
        if not (1 <= days <= 7):
            print("❌ 天数要在 1-7 之间哦\n")
            continue

        # ---- 6. 执行规划（网络/API 出错不崩溃，给友好提示）----
        try:
            plan_trip(city, days)
        except Exception as e:
            print(f"⚠️ 规划失败了：{e}\n请稍后再试（可能是网络或服务问题）\n")
            continue

if __name__ == "__main__":
    main()
