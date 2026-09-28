# 结构化输出：让 agent 返回 JSON（生产级关键技能）
# 学习计划 Day 5 —— 进阶：LLM 输出从"文本"变成"数据"
# 核心：response_format 强制 JSON → json.loads 解析 → 程序可编程处理
import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# 关键点：model_kwargs 里的 response_format 让模型"只输出 JSON"
llm = ChatOpenAI(
    model="deepseek-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0,
    model_kwargs={"response_format": {"type": "json_object"}},
)

prompt = (
    "为【成都】规划 3 日游，结合天气（毛毛雨，21°C）安排室内外活动。\n"
    "只输出 JSON，不要输出任何其他内容，严格按这个结构：\n"
    '{"city": "成都", "days": 3, "weather_style": "indoor",\n'
    ' "plan": [{"day": 1, "morning": "上午安排", "afternoon": "下午安排", "evening": "晚上安排"}, '
    '{"day": 2, ...}, {"day": 3, ...}],\n'
    ' "food": ["特色美食1", "特色美食2"],\n'
    ' "safety": ["注意事项1", "注意事项2"]}'
)

print("⏳ 让 LLM 生成结构化 JSON……")
resp = llm.invoke(prompt)
content = resp.content.strip()

# ===== 容错 1：LLM 偶尔会用 ``` 包 JSON，剥掉代码块标记 =====
if content.startswith("```"):
    content = content.replace("```", "").strip()
    if content.startswith("json"):
        content = content[4:].strip()

# ===== 容错 2：解析失败不崩溃，打印原始内容 =====
try:
    data = json.loads(content)          # JSON 字符串 → Python 字典
except json.JSONDecodeError as e:
    print("❌ LLM 输出的不是合法 JSON：", e)
    print("原始内容：", content)
    raise SystemExit

# ===== 消费端：拿到的是"数据"，想怎么处理都行 =====
print("\n" + "=" * 46)
print(f"🏙️ 城市：{data['city']} | 天数：{data['days']} | 风格：{data['weather_style']}")
print("=" * 46)
for p in data["plan"]:
    print(f"Day {p['day']}  上午：{p['morning']}")
    print(f"      下午：{p['afternoon']}")
    print(f"      晚上：{p['evening']}")
    print("-" * 46)
print("🍜 美食推荐：" + "、".join(data["food"]))
print("🛡️ 安全提醒：" + "；".join(data["safety"]))

# 进阶用法演示：JSON 数据可以直接存库/传前端/再加工
print("\n✅ 结构化完成——JSON 已可编程处理（比如存进 SQLite 或渲染成表格）")
