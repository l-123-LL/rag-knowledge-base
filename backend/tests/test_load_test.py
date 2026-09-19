from evaluation.load_test import build_questions, percentile, summarize


def test_build_questions_mixes_routes() -> None:
    questions = build_questions(16)

    assert len(questions) == 16
    assert all("question" in item for item in questions)
    assert any(item["expect"] == "faq" for item in questions)
    assert any(item["expect"] == "order_lookup" for item in questions)


def test_percentile_handles_empty_and_values() -> None:
    assert percentile([], 0.95) == 0.0
    assert percentile([10.0, 20.0, 30.0, 40.0], 0.50) == 30.0
    assert percentile([10.0, 20.0, 30.0, 40.0], 0.99) == 40.0


def test_summarize_computes_rates_and_codes() -> None:
    rows = [
        {"latency_ms": 10.0, "ok": True, "route": "order_lookup", "status_code": 200},
        {"latency_ms": 30.0, "ok": True, "route": "faq", "status_code": 200},
        {"latency_ms": 20.0, "ok": False, "route": "error", "status_code": 429},
    ]

    summary = summarize(rows, wall_seconds=0.1)

    assert summary["requests"] == 3
    assert summary["success"] == 2
    assert summary["success_rate"] == 0.6667
    assert summary["status_codes"] == {"200": 2, "429": 1}
    assert summary["routes"] == {"order_lookup": 1, "faq": 1}
    assert summary["throughput_rps"] == 30.0
