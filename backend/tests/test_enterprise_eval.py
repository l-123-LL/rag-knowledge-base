from evaluation.enterprise_eval import (
    build_evaluation_data,
    run_enterprise_evaluation,
)


def test_enterprise_evaluation_has_50_questions() -> None:
    _, questions = build_evaluation_data()

    assert len(questions) == 50


def test_enterprise_evaluation_runs() -> None:
    result = run_enterprise_evaluation()

    assert "average" in result
    assert result["average"]["hit@5"] >= 0.0
