from pathlib import Path

from app.ticket_store import create_ticket, list_tickets


def test_ticket_store_creates_and_lists_ticket(monkeypatch) -> None:
    ticket_dir = Path("test_ticket_data")
    monkeypatch.setenv("TICKET_DIR", str(ticket_dir))
    try:
        ticket = create_ticket("如何退货？", reason="manual")
        tickets = list_tickets()
    finally:
        (ticket_dir / f"{ticket['id']}.json").unlink(missing_ok=True)
        ticket_dir.rmdir()

    assert ticket["status"] == "open"
    assert tickets[0]["id"] == ticket["id"]
