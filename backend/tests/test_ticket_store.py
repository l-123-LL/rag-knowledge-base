from pathlib import Path

import app.ticket_store as ticket_store
from app.ticket_store import create_ticket, list_tickets


def test_ticket_store_creates_and_lists_ticket(monkeypatch) -> None:
    ticket_dir = Path("test_ticket_data")
    monkeypatch.setenv("TICKET_DIR", str(ticket_dir))
    try:
        ticket = create_ticket("如何退货？", reason="manual")
        tickets = list_tickets()
    finally:
        (ticket_dir / "default" / f"{ticket['id']}.json").unlink(missing_ok=True)
        (ticket_dir / "default").rmdir()
        ticket_dir.rmdir()

    assert ticket["status"] == "open"
    assert tickets[0]["id"] == ticket["id"]


def test_ticket_webhook_is_sent(monkeypatch) -> None:
    sent = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

    def fake_post(url, json, timeout):
        sent["url"] = url
        sent["json"] = json
        return FakeResponse()

    monkeypatch.setenv("TICKET_WEBHOOK_URL", "https://example.com/ticket")
    monkeypatch.setattr(ticket_store.httpx, "post", fake_post)
    ticket = {"id": "T1", "question": "投诉"}

    assert ticket_store.send_ticket_webhook(ticket) is True
    assert sent["url"] == "https://example.com/ticket"
    assert sent["json"]["id"] == "T1"
