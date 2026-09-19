from app.chunking import normalize_text, split_text, split_text_hierarchical


def test_normalize_text_keeps_paragraph_breaks() -> None:
    text = "第一段\r\n\r\n第二段"

    assert normalize_text(text) == "第一段\n\n第二段"


def test_short_paragraph_becomes_single_chunk() -> None:
    chunks = split_text("流感患者应尽早治疗。", chunk_size=20, overlap=3)

    assert len(chunks) == 1
    assert chunks[0].text == "流感患者应尽早治疗。"


def test_long_paragraph_uses_overlapping_windows() -> None:
    text = "医学知识" * 40

    chunks = split_text(text, chunk_size=20, overlap=4)

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 20 for chunk in chunks)
def test_hierarchical_split_keeps_parent_context() -> None:
    text = "第一段内容。" * 40 + "\n\n" + "第二段内容。" * 40

    children = split_text_hierarchical(text, parent_size=200, child_size=80, overlap=20)

    assert children
    for child in children:
        assert child.metadata["parent_id"].startswith("parent-")
        assert child.text in child.metadata["parent_text"]
    # 至少切成两个父块，说明确实做了分层
    assert len({child.metadata["parent_id"] for child in children}) >= 2
