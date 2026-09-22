# 第一个 API 脚本：请求一个公开接口并打印结果
# 学习计划 Day 1 —— HTTP 基础与 API 调用
import requests

# 1. 发起 GET 请求（向服务器"要"数据）
url = "https://jsonplaceholder.typicode.com/todos/1"
response = requests.get(url, timeout=10)

# 2. 查看状态码：200 表示成功
print("状态码:", response.status_code)

# 3. 把返回的 JSON 文本解析成 Python 字典
data = response.json()

# 4. 按字段打印
print("ID:", data["id"])
print("标题:", data["title"])
print("是否完成:", data["completed"])
