# Web 版智能旅行规划助手
# 学习计划 Day 5 —— 毕业工程：Flask Web 应用
# 浏览器输入城市 → 真实天气 → AI 生成行程 → 存入 SQLite
import html
from flask import Flask, request
from travel_memory import app as agent_app, save_plan, get_history, CITY_COORDS

web = Flask(__name__)

# ===== 页面框架（统一风格）=====
BASE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>智能旅行规划助手</title>
<style>
  body { font-family:"Microsoft YaHei",sans-serif; background:#F7FBF4; margin:0; padding:24px; color:#1F2329; }
  .wrap { max-width:760px; margin:0 auto; }
  .card { background:#fff; border:1px solid #DEE3E8; border-radius:12px; padding:24px; margin-bottom:16px; }
  h1 { color:#2E7D4F; font-size:26px; margin:0 0 4px; }
  h2 { color:#2E7D4F; font-size:19px; margin:0 0 12px; }
  .sub { color:#646A73; font-size:14px; margin-bottom:16px; }
  input { font-size:15px; padding:8px 12px; border-radius:6px; border:1px solid #B8C8BC; }
  button { font-size:15px; padding:9px 20px; border-radius:6px; background:#58AF78; color:#fff; border:none; cursor:pointer; font-weight:600; }
  button:hover { background:#2E8B57; }
  .err { background:#FFF3F0; border:1px solid #E8A08C; color:#B34A2E; padding:10px 14px; border-radius:8px; margin-bottom:16px; }
  pre { white-space:pre-wrap; font-family:inherit; background:#FAFAF8; border:1px solid #DEE3E8; border-radius:8px; padding:14px; line-height:1.7; }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th, td { border-bottom:1px solid #DEE3E8; padding:8px 10px; text-align:left; }
  th { background:#F0F7F2; }
  a { color:#2E8B57; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .ok { background:#F0F9F3; border:1px solid #A8D8B8; color:#2E7D4F; padding:8px 14px; border-radius:8px; margin-top:12px; font-size:13px; }
</style>
</head>
<body>
<div class="wrap">
__CONTENT__
</div>
</body>
</html>"""

def page(content: str) -> str:
    return BASE.replace("__CONTENT__", content)

def form_html(city: str = "", days: str = "3") -> str:
    """搜索表单（保留上次输入，失败时用户不用重打）"""
    return f"""<div class="card">
  <h1>智能旅行规划助手</h1>
  <div class="sub">输入城市和天数，AI 结合真实天气生成行程 · <a href="/history">查看历史记录</a></div>
  <form method="post" action="/plan">
    城市：<input name="city" value="{html.escape(city)}" placeholder="如：成都" style="width:150px;">
    天数：<input name="days" value="{days}" placeholder="1-7" style="width:60px;">
    <button type="submit">开始规划</button>
  </form>
</div>"""

def error_box(msg: str) -> str:
    return f'<div class="err">{html.escape(msg)}</div>'

# ===== 路由 1：主页（GET）=====
@web.route("/")
def home():
    return page(form_html())

# ===== 路由 2：规划（POST）=====
@web.route("/plan", methods=["POST"])
def plan():
    city = request.form.get("city", "").strip()
    days_str = request.form.get("days", "").strip()

    # 校验：城市
    if city not in CITY_COORDS:
        return page(form_html(city, days_str) + error_box(
            f"暂不支持「{city}」，支持：{'、'.join(CITY_COORDS)}"))
    # 校验：天数
    try:
        days = int(days_str)
    except ValueError:
        return page(form_html(city, days_str) + error_box("天数必须是数字，例如：3"))
    if not (1 <= days <= 7):
        return page(form_html(city, days_str) + error_box("天数要在 1-7 之间"))

    # 跑图（复用 travel_memory 的完整 agent）
    try:
        result = agent_app.invoke({"city": city, "days": days})
    except Exception as e:
        return page(form_html(city, days_str) + error_box(f"规划失败：{e}，请稍后再试"))

    # 存入长期记忆
    save_plan(city, days, result["trip_style"], result["itinerary"])

    # 结果页（html.escape 防 XSS：用户输入不能当 HTML 执行）
    body = form_html(city, days_str) + f"""<div class="card">
  <h2>{html.escape(city)} {days} 日游方案</h2>
  <pre>{html.escape(result['itinerary'])}</pre>
  <div class="ok">已存入历史记录（风格：{html.escape(result['trip_style'])}）</div>
</div>"""
    return page(body)

# ===== 路由 3：历史（GET）=====
@web.route("/history")
def history():
    rows = get_history(20)
    if not rows:
        trs = "<tr><td colspan='4'>还没有规划记录，去规划一次吧</td></tr>"
    else:
        trs = "".join(
            f"<tr><td>{html.escape(r[3])}</td><td>{html.escape(r[0])}</td><td>{r[1]} 日</td><td>{html.escape(r[2])}</td></tr>"
            for r in rows
        )
    body = form_html() + f"""<div class="card">
  <h2>历史记录</h2>
  <table><tr><th>时间</th><th>城市</th><th>天数</th><th>风格</th></tr>{trs}</table>
</div>"""
    return page(body)

if __name__ == "__main__":
    print("启动 Web 服务器：http://127.0.0.1:5000")
    web.run(host="127.0.0.1", port=5000)
