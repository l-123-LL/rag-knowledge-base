"""真实语料检索评测的打分口径测试（不加载模型）。"""

from evaluation.corpus_eval import score_question
from app.retrieval import RetrievedChunk


def _chunk(source: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(text=text, metadata={"source": source})


def test_score_question_separates_document_hit_from_evidence_hit() -> None:
    # 命中了正确的文档，但那段里没有证据句：文档级算中，证据级不算
    results = [
        _chunk("条例", "本条例适用于快递业务的监督管理。"),
        _chunk("条例", "经营快递业务的企业应当告知收件人当面验收。"),
    ]

    metrics = score_question(results, "条例", "当面验收")

    assert metrics["doc_hit@1"] == 1.0
    assert metrics["evidence_hit@1"] == 0.0
    assert metrics["evidence_hit@3"] == 1.0
    assert metrics["evidence_mrr"] == 0.5


def test_score_question_ignores_other_documents() -> None:
    results = [_chunk("平台说明", "订单支付后 24 小时内发货。当面验收不在本文档。")]

    metrics = score_question(results, "条例", "当面验收")

    assert metrics["doc_hit@1"] == 0.0
    assert metrics["evidence_hit@1"] == 0.0
    assert metrics["evidence_mrr"] == 0.0


def test_score_question_matches_english_keyword_case_insensitively() -> None:
    # 语料里写的是小写 nacos，标注写的是 Nacos，不能因此判成未命中
    results = [_chunk("微服务说明", "注册中心使用 nacos，默认端口 8848。")]

    metrics = score_question(results, "微服务说明", "Nacos")

    assert metrics["evidence_hit@1"] == 1.0
    assert metrics["evidence_mrr"] == 1.0
