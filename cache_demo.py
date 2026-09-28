# 缓存实战：函数结果缓存 + 过期缓存 + LLM 成本优化
# 学习计划 Day 5 —— 进阶：拿空间换时间、换钱
# 三种缓存：lru_cache（永久记住）/ TTLCache（过期）/ 实战 LLM 结果缓存（省 token）
import time
from functools import lru_cache
from cachetools import TTLCache

# ============================================================
# ① lru_cache：记住函数结果（标准库，零依赖）
#    同样参数只算一次，第二次直接命中
# ============================================================
@lru_cache(maxsize=32)   # 最多记住 32 个结果
def get_weather(city: str) -> str:
    """查询城市天气（模拟：真实场景这里调 Open-Meteo）"""
    print(f"  [真实请求] 查询 {city} 天气...")
    time.sleep(1)        # 模拟网络耗时
    return f"{city}：21°C 毛毛雨"

# ============================================================
# ② TTLCache：带过期时间的缓存（cachetools）
#    数据有时效性时用（天气 1 小时变一次、token 10 分钟过期）
# ============================================================
weather_cache = TTLCache(maxsize=64, ttl=5)   # 5 秒过期

def get_weather_ttl(city: str) -> str:
    if city in weather_cache:
        print(f"  [缓存命中] {city}")
        return weather_cache[city]
    print(f"  [真实请求] {city}...")
    time.sleep(1)
    weather_cache[city] = f"{city}：21°C"
    return weather_cache[city]

# ============================================================
# ③ 实战：LLM 行程缓存（省 token！）
#    同样「城市+天数」规划过就直接返回，不重复调大模型
# ============================================================
@lru_cache(maxsize=16)
def plan_trip_cached(city: str, days: int) -> str:
    """模拟 LLM 生成行程（真实场景：这里调 deepseek，花 token）"""
    print(f"  [LLM 调用] 生成 {city} {days}日游...（花 token）")
    return f"{city} {days}日游：D1 博物馆 → D2 美食街 → D3 茶馆"

if __name__ == "__main__":
    print("=== ① lru_cache：重复调用不重复请求 ===")
    print(" ", get_weather("北京"))
    print(" ", get_weather("北京"))   # 没打印 [真实请求] = 命中缓存
    print(" ", get_weather("上海"))
    print()

    print("=== ② TTLCache：过期后自动重新请求 ===")
    print(" ", get_weather_ttl("成都"))
    print(" ", get_weather_ttl("成都"))   # 命中缓存
    print("  等待 6 秒让缓存过期...")
    time.sleep(6)
    print(" ", get_weather_ttl("成都"))   # 过期 → 重新请求
    print()

    print("=== ③ 实战：LLM 行程缓存（省 token）===")
    print(" ", plan_trip_cached("成都", 3))   # 第一次：真调 LLM（花 token）
    print(" ", plan_trip_cached("成都", 3))   # 第二次：直接缓存（不花 token！）
    print(" ", plan_trip_cached("广州", 2))   # 新参数：真调 LLM
    print()
    print("✅ 结论：用户重复问「成都 3 日游」，第二次起零成本秒回")
