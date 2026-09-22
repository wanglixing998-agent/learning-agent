# 提示词工程进阶：Few-shot 与思维链
# 学习计划 Day 2 —— 提示词技巧实测
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

def ask(messages, temperature=0):
    """封装一次对话请求"""
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content

# ========== Few-shot：给两个例子，模型模仿格式 ==========
print("=" * 50)
print("【Few-shot 示例】把口语改成朋友圈文案风格")
few_shot = ask([
    {"role": "system", "content": "把口语化句子改写成朋友圈风格。"},
    # 示例 1
    {"role": "user", "content": "昨天晚上刮风刮的心烦"},
    {"role": "assistant", "content": "昨夜西风凋碧树。"},
    # 示例 2
    {"role": "user", "content": "人生起起落落，哪有那么多事"},
    {"role": "assistant", "content": "看云起云落，淡泊。"},
    # 真正的任务
    {"role": "user", "content": "心烦，静心"},
])
print(few_shot)

# ========== 思维链：让模型一步步推理 ==========
print("=" * 50)
print("【思维链示例】对比：不让思考 vs 让一步一步思考")
# 不加思维链
direct = ask([
    {"role": "system", "content": "你是数学助教。"},
    {"role": "user", "content": "食堂有 3 个窗口。第一个窗口 12 分钟卖完 36 份饭，第二个窗口 15 分钟卖完 30 份，第三个窗口 10 分钟卖完 40 份。哪个窗口卖得最快？"},
])
print("【直接回答】", direct)
print("-" * 30)
# 加思维链
with_cot = ask([
    {"role": "system", "content": "你是数学助教。请一步一步推理，最后用“答案：”给出结论。"},
    {"role": "user", "content": "食堂有 3 个窗口。第一个窗口 12 分钟卖完 36 份饭，第二个窗口 15 分钟卖完 30 份，第三个窗口 10 分钟卖完 40 份。哪个窗口卖得最快？"},
])
print("【逐步思考】", with_cot)
