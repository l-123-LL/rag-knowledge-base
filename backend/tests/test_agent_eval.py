from collections import Counter
from pathlib import Path

import pytest

from evaluation.agent_eval import load_tasks, run_evaluation


@pytest.fixture(autouse=True)
def isolated_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TRACE_DIR", str(tmp_path / "traces"))
    monkeypatch.setenv("TICKET_DIR", str(tmp_path / "tickets"))


def test_task_set_has_150_tasks_with_expected_composition() -> None:
    tasks = load_tasks()
    counts = Counter(task["type"] for task in tasks)

    assert len(tasks) == 150
    assert counts["knowledge"] == 50
    assert counts["order"] == 25
    assert counts["logistics"] == 15
    assert counts["policy"] == 15
    assert counts["handoff"] == 13
    assert counts["no_answer"] + counts["injection"] == 12
    assert counts["multiturn"] == 20


def test_smoke_run_produces_metrics() -> None:
    report = run_evaluation(tag="smoke")
    summary = report["summary"]

    assert summary["task_count"] == 25
    for key in (
        "task_success_rate",
        "route_accuracy",
        "tool_argument_accuracy",
        "citation_accuracy",
        "handoff_recall",
        "auto_resolve_rate",
    ):
        assert 0.0 <= summary[key] <= 1.0


def test_injection_tasks_expect_escalation() -> None:
    tasks = {task["id"]: task for task in load_tasks()}

    assert tasks["n05"]["must_escalate"] is True
    assert "系统提示词" in tasks["n05"]["question"]
