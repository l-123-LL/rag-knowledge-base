from evaluation.generation_eval import run_generation_evaluation


class FakeJudge:
    def score(
        self,
        question: str,
        answer: str,
        contexts: list[str],
    ) -> dict[str, float]:
        return {"faithfulness": 0.9, "relevance": 0.8}


def test_run_generation_evaluation() -> None:
    result = run_generation_evaluation(
        [
            {
                "question": "如何退货？",
                "answer": "7 天内可申请。",
                "contexts": ["收到商品后 7 天内可申请无理由退货。"],
            }
        ],
        FakeJudge(),
    )

    assert result["average"]["faithfulness"] == 0.9
    assert result["average"]["relevance"] == 0.8
