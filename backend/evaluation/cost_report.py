"""从真实问答日志里算成本：单次多少钱、一千次多少钱、钱花在哪。

为什么要单独做这个：README 里如果只写"按官方价估算"就是空话。这里直接读
`backend/data/logs/ask.jsonl`（每次调用都记录了真实 token 用量），把单价乘出来，
顺带给出 token 分布和"哪条路不花钱"的对比。

用法（backend 目录下）：
    ..\\.venv\\Scripts\\python.exe -m evaluation.cost_report
    ..\\.venv\\Scripts\\python.exe -m evaluation.cost_report --log data/logs/ask.jsonl
"""

import json
import os
from pathlib import Path

from app import config  # noqa: F401  加载 backend/.env，取单价配置
from app.cost import calculate_cost


def load_events(path: Path) -> list[dict]:
    """读日志；被强杀时最后一行可能是半截 JSON，跳过即可。"""
    events: list[dict] = []
    if not path.exists():
        return events
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def summarize(
    events: list[dict],
    input_price_per_million: float,
    output_price_per_million: float,
) -> dict:
    """按路由聚合 token 与成本。只有真正调用大模型的路由才有 token。"""
    by_route: dict[str, dict] = {}
    for event in events:
        route = str(event.get("route", "unknown"))
        usage = event.get("usage") or {}
        entry = by_route.setdefault(
            route,
            {"calls": 0, "llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost": 0.0},
        )
        entry["calls"] += 1
        if not usage:
            continue

        entry["llm_calls"] += 1
        entry["prompt_tokens"] += int(usage.get("prompt_tokens", 0))
        entry["completion_tokens"] += int(usage.get("completion_tokens", 0))
        cost = calculate_cost(
            usage,
            input_price_per_million=input_price_per_million,
            output_price_per_million=output_price_per_million,
        )
        entry["cost"] += float(cost or 0.0)

    total_calls = sum(item["calls"] for item in by_route.values())
    llm_calls = sum(item["llm_calls"] for item in by_route.values())
    total_cost = sum(item["cost"] for item in by_route.values())
    total_tokens = sum(
        item["prompt_tokens"] + item["completion_tokens"] for item in by_route.values()
    )

    return {
        "total_calls": total_calls,
        "llm_calls": llm_calls,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        # 单次成本按「调用大模型的次数」平均，否则会被零成本的 FAQ/规则路由稀释
        "cost_per_llm_call_usd": round(total_cost / llm_calls, 6) if llm_calls else None,
        "tokens_per_llm_call": round(total_tokens / llm_calls, 1) if llm_calls else None,
        "cost_per_1000_llm_calls_usd": (
            round(total_cost / llm_calls * 1000, 4) if llm_calls else None
        ),
        "by_route": by_route,
    }


def main(log_path: str | None = None) -> dict:
    input_price = float(os.getenv("DEEPSEEK_INPUT_PRICE_PER_MILLION", "0") or 0)
    output_price = float(os.getenv("DEEPSEEK_OUTPUT_PRICE_PER_MILLION", "0") or 0)
    path = Path(log_path or os.getenv("ASK_LOG_PATH", "data/logs/ask.jsonl"))
    summary = summarize(load_events(path), input_price, output_price)
    summary["log_path"] = str(path)
    summary["prices"] = {
        "input_per_million_usd": input_price,
        "output_per_million_usd": output_price,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not input_price and not output_price:
        print("提示：backend/.env 里的单价是 0，成本会算成 0；填上再跑一次才有意义。")
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="问答成本报告")
    parser.add_argument("--log", default=None, help="ask.jsonl 路径")
    main(parser.parse_args().log)
