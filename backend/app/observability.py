import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx


def forward_event(payload: dict) -> bool:
    # 可选外发，默认只写本地日志，不因外部平台不可用影响主流程。
    """可选外发：配置 OBSERVABILITY_WEBHOOK_URL 后可接 Langfuse 或告警平台。"""
    url = os.getenv("OBSERVABILITY_WEBHOOK_URL")
    if not url:
        return False

    try:
        response = httpx.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError:
        return False

    return True


def _load_events(path) -> list[dict]:
    """读取 JSONL 事件；损坏的半行（例如进程被强杀）直接跳过，不能让聚合接口崩掉。"""
    events: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def log_ask_event(event: dict, log_path: str | Path | None = None) -> None:
    """把一次问答的关键字段追加到 JSONL，方便离线分析和监控。"""
    """把问答事件追加到 JSONL 日志，后续可替换为 Langfuse。"""
    path = Path(log_path or os.getenv("ASK_LOG_PATH", "data/logs/ask.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        **event,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    forward_event(payload)


def summarize_ask_log(log_path: str | Path | None = None) -> dict:
    # 聚合日志用于 /metrics 和 /alerts，不加载大模型。
    path = Path(log_path or os.getenv("ASK_LOG_PATH", "data/logs/ask.jsonl"))
    if not path.exists():
        return {
            "total_queries": 0,
            "route_counts": {},
            "avg_latency_ms": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
        }

    events = _load_events(path)
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


def log_feedback(
    event: dict,
    log_path: str | Path | None = None,
) -> None:
    path = Path(log_path or os.getenv("FEEDBACK_LOG_PATH", "data/logs/feedback.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        **event,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    forward_event(payload)


def summarize_feedback(
    log_path: str | Path | None = None,
) -> dict:
    path = Path(
        log_path or os.getenv("FEEDBACK_LOG_PATH", "data/logs/feedback.jsonl")
    )
    if not path.exists():
        return {"feedback_count": 0, "helpful_rate": 0.0, "up_count": 0, "down_count": 0}

    events = _load_events(path)
    up_count = sum(1 for event in events if event.get("rating") == "up")
    down_count = sum(1 for event in events if event.get("rating") == "down")
    feedback_count = up_count + down_count
    return {
        "feedback_count": feedback_count,
        "up_count": up_count,
        "down_count": down_count,
        "helpful_rate": up_count / feedback_count if feedback_count else 0.0,
    }
