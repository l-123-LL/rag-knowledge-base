from pathlib import Path

from app.session_store import clear_session, get_history, record_message


def test_session_history_round_trip(monkeypatch) -> None:
    session_dir = Path("test_session_data")
    monkeypatch.setenv("SESSION_DIR", str(session_dir))
    session_id = "test-session"

    try:
        record_message(session_id, "user", "如何退货？")
        record_message(session_id, "assistant", "7 天内可申请。")
        history = get_history(session_id)
        clear_session(session_id)
    finally:
        (session_dir / "default" / "test-session.json").unlink(missing_ok=True)
        (session_dir / "default").rmdir()
        session_dir.rmdir()

    assert history[0]["role"] == "user"
    assert history[1]["content"] == "7 天内可申请。"
    assert get_history(session_id) == []
