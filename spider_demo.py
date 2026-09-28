# 爬虫实战：抓取豆瓣电影 Top250 标题 + 评分
# 学习计划 Day 5 —— 进阶：没有 API 时，怎么拿数据
# 流程：requests 请求 → BeautifulSoup 解析 → 选择器提取 → 数据落地
import requests
from bs4 import BeautifulSoup

# ===== 1. 请求网页 =====
# 反爬第一步：伪装成浏览器（User-Agent）
url = "https://movie.douban.com/top250"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}
print("⏳ 请求豆瓣 Top250……")
resp = requests.get(url, headers=headers, timeout=15)
print(f"    状态码：{resp.status_code}（200 = 成功；418/403 = 被反爬拦截）")

if resp.status_code != 200:
    raise SystemExit("被反爬拦截了，稍后再试")

# ===== 2. 解析 HTML =====
soup = BeautifulSoup(resp.text, "lxml")

# ===== 3. 用选择器提取数据 =====
# 豆瓣每部电影是一个 <li>，里面 .hd .title 是标题，.rating_num 是评分
items = soup.select(".grid_view li")
print(f"    找到 {len(items)} 部电影\n")

print("🏆 豆瓣电影 Top250（前 10 名）：")
print("-" * 46)
for i, item in enumerate(items[:10], 1):
    title = item.select_one(".hd .title").text.strip()   # 标题
    rating = item.select_one(".rating_num").text.strip()  # 评分
    quote = item.select_one(".quote .inq")               # 一句话短评（可能没有）
    quote_text = quote.text.strip() if quote else "（无短评）"
    print(f"{i:2d}. {title}  ⭐{rating}")
    print(f"    {quote_text}")
print("-" * 46)

# ===== 4. 数据落地：存成文件（下次不用重新爬）=====
with open(r"D:\workspace\learning-agent\douban_top10.txt", "w", encoding="utf-8") as f:
    for i, item in enumerate(items[:10], 1):
        title = item.select_one(".hd .title").text.strip()
        rating = item.select_one(".rating_num").text.strip()
        f.write(f"{i}. {title} | {rating}\n")
print("✅ 已保存到 douban_top10.txt")
