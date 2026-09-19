from evaluation.generation_report import human_review_sheet, summarize_scores, to_markdown


def test_summarize_scores_computes_means_and_low_scores() -> None:
    rows = [
        {"id": "a", "type": "faq", "question": "退货要几天", "answer": "7 天内。", "faithfulness": 1.0, "relevance": 1.0},
        {"id": "b", "type": "order", "question": "订单状态", "answer": "已发货。", "faithfulness": 0.5, "relevance": 0.5},
        {"id": "c", "type": "no_answer", "question": "今天天气", "answer": "无法确认。", "faithfulness": 0.0, "relevance": 0.0},
    ]

    summary = summarize_scores(rows)

    assert summary["case_count"] == 3
    assert summary["faithfulness_mean"] == 0.5
    assert summary["relevance_mean"] == 0.5
    assert summary["low_score_count"] == 2
    assert summary["low_score_rate"] == 0.6667
    assert {item["id"] for item in summary["low_score_cases"]} == {"b", "c"}


def test_summarize_scores_handles_empty_input() -> None:
    summary = summarize_scores([])

    assert summary["case_count"] == 0
    assert summary["low_score_rate"] == 0.0


def test_markdown_report_lists_low_score_cases() -> None:
    rows = [
        {"id": "c", "type": "no_answer", "question": "今天天气", "answer": "编造的答案", "faithfulness": 0.0, "relevance": 0.0},
    ]
    summary = summarize_scores(rows)

    markdown = to_markdown(summary, {"created_at": "2026-09-19", "model": "deepseek-chat"})

    assert "# 生成质量评估报告（LLM-as-Judge）" in markdown
    assert "低分样本" in markdown
    assert "编造的答案" in markdown


def test_human_review_sheet_has_blank_human_columns() -> None:
    rows = [
        {
            "id": "a",
            "question": "退货要几天",
            "answer": "7 天内。",
            "contexts": ["收到商品后 7 天内可申请无理由退货。"],
            "faithfulness": 1.0,
            "relevance": 1.0,
        }
    ]

    sheet = human_review_sheet(rows, sample_size=5)

    assert "人工复核抽样表" in sheet
    assert "| a |" in sheet
    # 人工列留空：每行以 "| 1.0 |  | 1.0 |  |" 结尾（两个空的待填列）
    assert "| 1.0 |  | 1.0 |  |" in sheet
