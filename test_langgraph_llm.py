# 单元测试：验证 parse_decision 的路由逻辑
# 学习计划 Day 4 —— 不依赖 LLM、不依赖真实天气，独立验证逻辑
import sys
sys.path.insert(0, r"D:\workspace\learning-agent")

from langgraph_llm import parse_decision


def test_storm_goes_to_storm_plan():
    """雷暴 → storm_plan 分支"""
    assert parse_decision("storm") == "storm_plan"
    assert parse_decision("  STORM ") == "storm_plan"          # 带空格+大写
    assert parse_decision("有雷暴，storm") == "storm_plan"      # 混在句子里


def test_outdoor_goes_to_outdoor_plan():
    """晴天 → outdoor_plan 分支"""
    assert parse_decision("outdoor") == "outdoor_plan"
    assert parse_decision("天气晴好，outdoor 合适") == "outdoor_plan"
    assert parse_decision("Outdoor!") == "outdoor_plan"


def test_indoor_goes_to_indoor_plan():
    """下雨/默认 → indoor_plan 分支"""
    assert parse_decision("indoor") == "indoor_plan"
    assert parse_decision("下雨了 indoor") == "indoor_plan"
    assert parse_decision("随便说了点别的") == "indoor_plan"    # 兜底默认


def test_storm_priority_over_outdoor():
    """雷暴优先于户外（storm 单词里不含 outdoor 关键词，但要保证顺序）"""
    assert parse_decision("storm and outdoor") == "storm_plan"
