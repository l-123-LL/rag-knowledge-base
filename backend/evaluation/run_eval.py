import json
from pathlib import Path

from app.evaluation import resolve_embedder, run_retrieval_evaluation


def main(embedder_name: str = "bge") -> None:
    base = Path(__file__).resolve().parent
    corpus = json.loads((base / "sample_corpus.json").read_text(encoding="utf-8"))
    questions = json.loads(
        (base / "sample_questions.json").read_text(encoding="utf-8")
    )
    result = run_retrieval_evaluation(
        corpus,
        questions,
        embedder=resolve_embedder(embedder_name),
    )
    print(json.dumps(result["average"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="样例语料检索评测")
    parser.add_argument("--embedder", default="bge", choices=["bge", "hash"])
    main(parser.parse_args().embedder)
