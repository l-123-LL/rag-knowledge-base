from pathlib import Path

import pytest

from app.trace_store import (
    count_traces,
    mask_payload,
    mask_pii,
    new_trace_id,
    read_trace,
    write_trace,
)


@pytest.fixture(autouse=True)
def isolated_trace_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TRACE_DIR", str(tmp_path / "traces"))


def test_mask_pii_covers_phone_email_and_id_card() -> None:
    text = "联系我 13800138000 或 user@example.com，身份证 110101199001011234"

    masked = mask_pii(text)

    assert "13800138000" not in masked
    assert "138****8000" in masked
    assert "user@example.com" not in masked
    assert "110101199001011234" not in masked


def test_mask_payload_handles_nested_structures() -> None:
    payload = {"question": "手机号 13900139000", "steps": [{"detail": "邮箱 a@b.com"}]}

    masked = mask_payload(payload)

    assert masked["question"] == "手机号 139****9000"
    assert masked["steps"][0]["detail"] == "邮箱 [email]"


def test_trace_is_written_masked_and_readable() -> None:
    trace_id = new_trace_id()
    write_trace(
        {
            "trace_id": trace_id,
            "tenant_id": "default",
            "question": "订单人电话 13800138000 要退款",
            "steps": [{"step": 1, "action": "intent"}],
        }
    )

    record = read_trace(trace_id)

    assert record is not None
    assert "13800138000" not in record["question"]
    assert record["steps"] == [{"step": 1, "action": "intent"}]
    assert count_traces() == 1


def test_read_trace_returns_none_for_unknown_id() -> None:
    assert read_trace("tr_not_exists") is None
