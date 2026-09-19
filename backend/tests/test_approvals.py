from pathlib import Path

import pytest

from app.approvals import (
    build_idempotency_key,
    count_pending,
    create_approval,
    get_approval,
    list_approvals,
    save_approval,
)


@pytest.fixture(autouse=True)
def isolated_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPROVAL_DIR", str(tmp_path / "approvals"))
    monkeypatch.setenv("TICKET_DIR", str(tmp_path / "tickets"))


def test_create_approval_is_idempotent_by_key() -> None:
    payload = {"order_id": "SO20260901001", "reason": "other"}

    first = create_approval("refund_request", payload, tenant_id="default")
    second = create_approval("refund_request", payload, tenant_id="default")

    assert first["id"] == second["id"]
    assert len(list_approvals("default")) == 1
    assert count_pending("default") == 1


def test_same_payload_in_other_tenant_is_separate() -> None:
    payload = {"order_id": "SO20260901019", "reason": "other"}

    default_one = create_approval("refund_request", payload, tenant_id="default")
    acme_one = create_approval("refund_request", payload, tenant_id="acme")

    assert default_one["id"] != acme_one["id"]
    assert list_approvals("acme")[0]["tenant_id"] == "acme"


def test_idempotency_key_is_stable_regardless_of_key_order() -> None:
    key_one = build_idempotency_key("t", {"a": 1, "b": 2}, "default")
    key_two = build_idempotency_key("t", {"b": 2, "a": 1}, "default")

    assert key_one == key_two


def test_decide_and_persist_approval() -> None:
    record = create_approval("refund_request", {"order_id": "SO20260901001"}, tenant_id="default")
    record["status"] = "approved"
    save_approval(record)

    stored = get_approval(record["id"], tenant_id="default")

    assert stored is not None
    assert stored["status"] == "approved"
    assert count_pending("default") == 0


def test_get_approval_respects_tenant_scope() -> None:
    record = create_approval("refund_request", {"order_id": "SO20260901001"}, tenant_id="default")

    assert get_approval(record["id"], tenant_id="acme") is None
