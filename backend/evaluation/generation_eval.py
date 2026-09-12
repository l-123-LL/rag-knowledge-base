from app.judge import Judge


def run_generation_evaluation(cases: list[dict], judge: Judge) -> dict:
    per_case = []
    for case in cases:
        scores = judge.score(
            question=case["question"],
            answer=case["answer"],
            contexts=case.get("contexts", []),
        )
        per_case.append({**case, **scores})

    if not per_case:
        return {"per_case": [], "average": {}}

    keys = [key for key in ("faithfulness", "relevance") if key in per_case[0]]
    average = {
        key: sum(item[key] for item in per_case) / len(per_case)
        for key in keys
    }
    return {"per_case": per_case, "average": average}
