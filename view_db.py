# 查看 SQLite 数据库内容（正确打开 .db 的方式）
import sqlite3

conn = sqlite3.connect(r"D:\workspace\learning-agent\travel_memory.db")
cur = conn.cursor()

# 1. 列出数据库里有哪些表
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("📋 数据库里的表：", [r[0] for r in cur.fetchall()])

# 2. 查看 preferences 表（用户偏好）
cur.execute("SELECT * FROM preferences")
print("\n🧠 用户偏好：")
for row in cur.fetchall():
    print("  ", row)

# 3. 查看 plans 表（行程历史）
cur.execute("SELECT id, city, days, style, created_at FROM plans")
print("\n🗂️ 行程历史：")
for row in cur.fetchall():
    print("  ", row)

conn.close()
