# 生产级 API 调用：超时 + 重试 + 限流 + 异步 + 队列
# 学习计划 Day 5 —— 进阶：应用层并发工程
# 这些就是你入职大模型公司做业务开发每天要用的东西
import time
import queue
import asyncio
import requests

# ============================================================
# ① 超时 + 重试（指数退避 + 429 限流处理）
# ============================================================
def call_with_retry(url: str, params: dict = None, max_retries: int = 3, timeout: int = 10):
    """带重试的 GET 请求：
    网络超时/断连 → 自动重试（越等越久）
    被限流(429)  → 按服务端要求等待后重试
    其他 HTTP 错误 → 直接抛（不浪费重试）"""
    headers = {"User-Agent": "Mozilla/5.0 (learning)"}
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()              # 非 2xx 抛异常
            return resp.json()                   # 成功直接返回
        except requests.Timeout:
            wait = 2 ** attempt                  # 指数退避：1s → 2s → 4s
            print(f"  ⏱ 第{attempt+1}次超时，{wait}s 后重试")
            time.sleep(wait)
        except requests.ConnectionError:
            wait = 2 ** attempt
            print(f"  🔌 第{attempt+1}次连接失败，{wait}s 后重试")
            time.sleep(wait)
        except requests.HTTPError as e:
            if e.response.status_code == 429:    # 被限流！
                wait = int(e.response.headers.get("Retry-After", 5))
                print(f"  🚦 被限流(429)，等待 {wait}s（服务端指定的时间）")
                time.sleep(wait)
            else:
                print(f"  ❌ HTTP {e.response.status_code}")
                raise                            # 其他错误不重试
    raise RuntimeError(f"重试 {max_retries} 次仍失败：{url}")

# ============================================================
# ② 限流：控制调用频率（令牌桶简化版）
# ============================================================
class RateLimiter:
    """保证每 min_interval 秒最多调用一次 API"""
    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self.last_call = 0.0

    def wait(self):
        """每次调 API 前调用：如果太频繁就睡一会"""
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()

# ============================================================
# ③ 异步：多个请求并行（asyncio）
# ============================================================
async def fetch_one(name: str, delay: float) -> str:
    """模拟一次耗时 API 调用（真实场景用 httpx/aiohttp 才是真并行）"""
    await asyncio.sleep(delay)
    return f"  {name} 完成（耗时 {delay}s）"

async def fetch_all():
    """3 个请求并行：总耗时 ≈ 最慢的那个，而不是相加"""
    tasks = [fetch_one("北京", 2), fetch_one("上海", 2), fetch_one("广州", 2)]
    return await asyncio.gather(*tasks)

# ============================================================
# ④ 队列：任务排队（生产环境：用户请求先进队列，worker 逐个处理）
# ============================================================
def queue_demo():
    q = queue.Queue()
    for city in ["北京", "上海", "广州", "成都"]:
        q.put(f"任务：查{city}天气")
    print(f"  队列里待处理任务：{q.qsize()} 个")
    while not q.empty():
        print(f"  处理 → {q.get()}")
    print("  队列已清空")

# ============================================================
# 主演示
# ============================================================
if __name__ == "__main__":
    # --- ① 重试：故意访问不存在的路径，看它自动重试 ---
    print("=== ① 超时+重试（访问一个不存在的接口）===")
    try:
        call_with_retry("https://api.open-meteo.com/v1/not-exist")
    except Exception as e:
        print(f"  最终失败：{e}\n")

    # --- ② 限流：1 秒内调 3 次，看时间间隔 ---
    print("=== ② 限流（每 0.5 秒最多调一次）===")
    limiter = RateLimiter(min_interval=0.5)
    for i in range(3):
        limiter.wait()
        print(f"  第 {i+1} 次调用（时间戳 {time.time():.1f}）")
    print()

    # --- ③ 异步：3 个请求并行 ---
    print("=== ③ 异步并行（3 个 2 秒任务同时跑）===")
    start = time.time()
    results = asyncio.run(fetch_all())
    for r in results:
        print(r)
    print(f"  总耗时：{time.time()-start:.1f}s（串行需要 6s）\n")

    # --- ④ 队列 ---
    print("=== ④ 任务队列 ===")
    queue_demo()
