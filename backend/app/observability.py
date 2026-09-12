import json
import os
from datetime import datetime, timezone
from pathlib import Path


def log_ask_event(event: dict, log_path: str | Path | None = None) -> None:
    """把问答事件追加到 JSONL 日志，后续可替换为 Langfuse。"""
    path = Path(log_path or os.getenv("ASK_LOG_PATH", "data/logs/ask.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def summarize_ask_log(log_path: str | Path | None = None) -> dict:
    path = Path(log_path or os.getenv("ASK_LOG_PATH", "data/logs/ask.jsonl"))
    if not path.exists():
        return {
            "total_queries": 0,
            "route_counts": {},
            "avg_latency_ms": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
        }

    events = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    latencies = [
        event["latency_ms"]
        for event in events
        if isinstance(event.get("latency_ms"), (int, float))
    ]
    route_counts: dict[str, int] = {}
    total_tokens = 0
    total_cost = 0.0

    for event in events:
        route = str(event.get("route", "unknown"))
        route_counts[route] = route_counts.get(route, 0) + 1
        usage = event.get("usage") or {}
        total_tokens += int(usage.get("total_tokens", 0))
        if isinstance(event.get("cost"), (int, float)):
            total_cost += float(event["cost"])

    return {
        "total_queries": len(events),
        "route_counts": route_counts,
        "avg_latency_ms": int(sum(latencies) / len(latencies)) if latencies else 0,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
    }
