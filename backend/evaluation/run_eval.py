import json
from pathlib import Path

from app.evaluation import run_retrieval_evaluation


def main() -> None:
    base = Path(__file__).resolve().parent
    corpus = json.loads((base / "sample_corpus.json").read_text(encoding="utf-8"))
    questions = json.loads(
        (base / "sample_questions.json").read_text(encoding="utf-8")
    )
    result = run_retrieval_evaluation(corpus, questions)
    print(json.dumps(result["average"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
