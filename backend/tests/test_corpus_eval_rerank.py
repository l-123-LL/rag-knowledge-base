"""重排 A/B 对比链路的测试。

真实重排模型（BAAI/bge-reranker-base）有 1.1GB，CI 和本机受限网络都不适合拉，
所以这里用一个确定性的假重排器把「对比逻辑」本身验证掉：只要权重到位，
`corpus_eval --compare-rerank` 就能直接给出真实数字。
"""

import json
from pathlib import Path

from app.retrieval import RetrievedChunk
from evaluation.corpus_eval import build_retriever, load_corpus, score_question


class ReverseReranker:
    """把候选顺序倒过来，用来确认重排真的影响了排序与指标。"""

    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        for index, chunk in enumerate(chunks):
            chunk.rerank_score = float(index)
            chunk.combined_score = float(index)
        return list(reversed(chunks))


class FakeEmbedder:
    def __init__(self, dimensions: int = 32) -> None:
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for char in text:
                vector[ord(char) % self.dimensions] += 1.0
            vectors.append(vector)
        return vectors


def test_reranker_changes_ordering_and_metrics() -> None:
    corpus = [
        ("甲文档", "快递签收前可以先验收再签收。"),
        ("乙文档", "退货运费由谁承担要看责任方。"),
    ]
    query = "签收前可以先验收吗"

    plain = build_retriever(corpus, FakeEmbedder())
    reranked = build_retriever(corpus, FakeEmbedder(), reranker=ReverseReranker())

    plain_top = plain.search(query, top_k=2)[0].text
    reranked_top = reranked.search(query, top_k=2)[0].text

    assert plain_top != reranked_top  # 重排确实改变了 top1
    assert score_question(plain.search(query, top_k=2), "甲文档", "当面验收")[
        "doc_hit@1"
    ] == 1.0
    # 被倒序之后，命中的文档掉到第二位
    assert score_question(reranked.search(query, top_k=2), "甲文档", "验收")[
        "doc_hit@1"
    ] == 0.0
    assert score_question(reranked.search(query, top_k=2), "甲文档", "验收")[
        "doc_hit@3"
    ] == 1.0


def test_question_set_labels_point_at_real_corpus_files() -> None:
    # 标注里的 source 必须真的存在于 backend/corpus，否则指标没有意义
    base = Path(__file__).resolve().parents[1] / "evaluation"
    questions = json.loads(
        (base / "corpus_eval_questions.json").read_text(encoding="utf-8")
    )["questions"]
    available = {source for source, _ in load_corpus(base.parent / "corpus")}

    missing = {item["source"] for item in questions} - available

    assert not missing, f"标注引用了不存在的语料文件：{missing}"
