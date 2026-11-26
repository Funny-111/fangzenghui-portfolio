"""单任务成本计算 —— 真实 token × 官方单价

价格来源：DeepSeek-V4.1-Flash-1017 官方价格表（2026-11-05 Funny 提供）。
单价变动或换模型时只改本文件的 PRICES，再重跑 scripts/cost_report.py。
"""
# 元 / 百万 tokens
PRICES = {
    "input_miss": {"idle": 1.0, "peak": 2.0},   # 输入·缓存未命中
    "input_hit": {"idle": 0.02, "peak": 0.04},  # 输入·缓存命中（日志无标记，仅备注用）
    "output": {"idle": 4.0, "peak": 8.0},       # 输出
}


def cost_yuan(input_tokens: int, output_tokens: int, period: str) -> float:
    """单次查询成本（元）。period: idle 空闲 / peak 高峰。

    输入按缓存未命中计价 → 结果是成本上界（命中缓存只会更低）。
    """
    return (
        input_tokens / 1e6 * PRICES["input_miss"][period]
        + output_tokens / 1e6 * PRICES["output"][period]
    )
