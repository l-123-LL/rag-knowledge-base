"""最小执行轨迹：按天写 JSONL，按 trace_id 回读，写入前统一脱敏。

不引入追踪平台，复用现有 JSONL 思路；日志与轨迹都不允许出现手机号、
邮箱、证件号与 API Key。
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path


PHONE_PATTERN = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
ID_CARD_PATTERN = re.compile(r"(?<!\d)(\d{17}[\dXx]|\d{15})(?!\d)")
API_KEY_PATTERN = re.compile(r"\b(sk-[A-Za-z0-9]{8,}|[A-Za-z0-9_-]{32,})\b")


def mask_pii(text: str) -> str:
    """对文本做基础脱敏，覆盖手机号、邮箱、证件号与疑似 Key。"""
    if not text:
        return text

    masked = PHONE_PATTERN.sub(lambda m: f"{m.group(1)[:3]}****{m.group(1)[-4:]}", text)
    masked = EMAIL_PATTERN.sub("[email]", masked)
    masked = ID_CARD_PATTERN.sub("[id-card]", masked)
    masked = API_KEY_PATTERN.sub("[redacted]", masked)
    return masked


def mask_payload(value):
    """递归脱敏任意结构，dict / list / str 都支持。"""
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, dict):
        return {key: mask_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [mask_payload(item) for item in value]
    return value


def new_trace_id() -> str:
    return f"tr_{uuid.uuid4().hex[:16]}"


def _trace_dir() -> Path:
    return Path(os.getenv("TRACE_DIR", "data/traces"))


def write_trace(trace: dict) -> str:
    """追加一条轨迹，返回 trace_id。按天分文件，避免单文件无限增长。"""
    directory = _trace_dir()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = directory / f"trace-{stamp}.jsonl"

    payload = mask_payload(trace)
    payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return str(payload.get("trace_id", ""))


def read_trace(trace_id: str) -> dict | None:
    """按 trace_id 在按天文件里倒序查找，返回最近一条。"""
    directory = _trace_dir()
    if not directory.exists():
        return None

    for path in sorted(directory.glob("trace-*.jsonl"), reverse=True):
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("trace_id") == trace_id:
                return record
    return None


def count_traces() -> int:
    directory = _trace_dir()
    if not directory.exists():
        return 0

    total = 0
    for path in directory.glob("trace-*.jsonl"):
        total += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return total
