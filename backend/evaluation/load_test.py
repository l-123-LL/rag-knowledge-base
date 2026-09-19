"""并发压测脚本：默认只打不依赖外部模型的路径（订单 / FAQ / 转人工），零 API 花费。

用法：
    python -m evaluation.load_test --concurrency 1,5,10,20 --requests 40
    python -m evaluation.load_test --include-model      # 加入知识问答（会调用 DeepSeek，花钱）

注意：后端默认限流 120 次/分钟/IP，压测时会看到 429，这属于设计行为；
要测原始吞吐，用 docker-compose.loadtest.yml 覆盖关掉限流再跑。
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parent

ORDER_QUESTIONS = [
    {"question": "订单 SO20260901001 现在什么状态", "expect": "order_lookup"},
    {"question": "SO20260901006 的物流到哪了", "expect": "logistics_track"},
    {"question": "订单 SO20260901003 什么时候能发货", "expect": "order_lookup"},
    {"question": "SO20260901009 的物流轨迹", "expect": "logistics_track"},
]
FAQ_QUESTIONS = [
    {"question": "退货要几天", "expect": "faq"},
    {"question": "发票怎么申请", "expect": "faq"},
    {"question": "发货一般要多久", "expect": "faq"},
]
HANDOFF_QUESTIONS = [
    {"question": "我要投诉你们的物流", "expect": "workflow"},
]


def build_questions(total: int, include_model: bool = False) -> list[dict]:
    """构造混合问题集：订单为主，夹杂 FAQ 与转人工。"""
    pool = ORDER_QUESTIONS * 3 + FAQ_QUESTIONS + HANDOFF_QUESTIONS
    if include_model:
        pool = pool + [{"question": "保修期内维修怎么处理", "expect": "knowledge_search+deepseek"}]
    return [dict(pool[index % len(pool)]) for index in range(total)]


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * ratio))
    return round(ordered[index], 1)


def summarize(rows: list[dict], wall_seconds: float) -> dict:
    latencies = [row["latency_ms"] for row in rows]
    success = [row for row in rows if row["ok"]]
    routes = Counter(row["route"] for row in success)
    codes = Counter(str(row["status_code"]) for row in rows)
    return {
        "requests": len(rows),
        "success": len(success),
        "success_rate": round(len(success) / len(rows), 4) if rows else 0.0,
        "status_codes": dict(codes),
        "latency_p50_ms": percentile(latencies, 0.50),
        "latency_p95_ms": percentile(latencies, 0.95),
        "latency_p99_ms": percentile(latencies, 0.99),
        "latency_mean_ms": round(statistics.mean(latencies), 1) if latencies else 0.0,
        "throughput_rps": round(len(rows) / wall_seconds, 2) if wall_seconds > 0 else 0.0,
        "routes": dict(routes),
    }


def run_level(
    base_url: str,
    questions: list[dict],
    concurrency: int,
    timeout: float,
) -> dict:
    """以固定并发打完一轮问题，返回统计结果。"""
    def call(item: dict) -> dict:
        started = time.perf_counter()
        status_code = 0
        route = "error"
        ok = False
        try:
            response = httpx.post(
                f"{base_url}/ask",
                json={"question": item["question"], "workflow_mode": "tools"},
                timeout=timeout,
            )
            status_code = response.status_code
            if response.status_code == 200:
                payload = response.json()
                route = payload.get("model", "unknown")
                ok = payload.get("status") in {"done", "insufficient"}
        except httpx.HTTPError:
            route = "transport_error"
        return {
            "question": item["question"],
            "latency_ms": (time.perf_counter() - started) * 1000,
            "status_code": status_code,
            "route": route,
            "ok": ok,
        }

    wall_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        rows = list(pool.map(call, questions))
    wall_seconds = time.perf_counter() - wall_started

    summary = summarize(rows, wall_seconds)
    summary["concurrency"] = concurrency
    summary["wall_seconds"] = round(wall_seconds, 2)
    return summary


def to_markdown(results: list[dict], meta: dict) -> str:
    lines = [
        "# 并发压测报告",
        "",
        f"- 目标：{meta['base_url']}",
        f"- 时间：{meta['created_at']}",
        f"- 每轮请求数：{meta['requests']}；包含模型路径：{meta['include_model']}",
        "",
        "| 并发 | 成功数 | 成功率 | P50 | P95 | P99 | 吞吐(RPS) | 状态码 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        (
            f"| {item['concurrency']} | {item['success']}/{item['requests']} | "
            f"{item['success_rate']:.2%} | {item['latency_p50_ms']} ms | "
            f"{item['latency_p95_ms']} ms | {item['latency_p99_ms']} ms | "
            f"{item['throughput_rps']} | {item['status_codes']} |"
        )
        for item in results
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="并发压测")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--concurrency", default="1,5,10,20")
    parser.add_argument("--requests", type=int, default=40)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--include-model", action="store_true")
    args = parser.parse_args()

    levels = [int(value) for value in args.concurrency.split(",") if value.strip()]
    results = []
    for level in levels:
        questions = build_questions(args.requests, include_model=args.include_model)
        summary = run_level(args.url, questions, level, args.timeout)
        results.append(summary)
        print(
            f"并发 {level:>3}：成功 {summary['success']}/{summary['requests']}，"
            f"P95 {summary['latency_p95_ms']} ms，吞吐 {summary['throughput_rps']} RPS，"
            f"状态码 {summary['status_codes']}"
        )

    meta = {
        "base_url": args.url,
        "created_at": datetime.now(UTC).isoformat(),
        "requests": args.requests,
        "include_model": args.include_model,
    }
    report_dir = BASE_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    (report_dir / f"load-test-{stamp}.json").write_text(
        json.dumps({"meta": meta, "results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    markdown = to_markdown(results, meta)
    (report_dir / f"load-test-{stamp}.md").write_text(markdown, encoding="utf-8")
    print(f"\n报告已写入：{report_dir / f'load-test-{stamp}.md'}")


if __name__ == "__main__":
    main()
