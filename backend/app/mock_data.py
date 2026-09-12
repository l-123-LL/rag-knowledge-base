from .schemas import Citation, Source

sources: list[Source] = [
    Source(
        id="return-policy",
        title="退换货政策说明",
        category="售后政策",
        url="https://example.com/support/returns",
        status="indexed",
        updatedAt="2026-09-01",
        description="说明商品退换货条件、申请流程、运费规则和退款时效。",
    ),
    Source(
        id="shipping-policy",
        title="订单与物流说明",
        category="订单服务",
        url="https://example.com/support/shipping",
        status="indexed",
        updatedAt="2026-09-02",
        description="说明发货时间、物流查询方式、配送范围和异常处理。",
    ),
    Source(
        id="invoice-policy",
        title="发票申请说明",
        category="财务服务",
        url="https://example.com/support/invoice",
        status="pending",
        updatedAt="待更新",
        description="说明电子发票申请入口、开票信息填写和重开规则。",
    ),
    Source(
        id="account-policy",
        title="账号与会员说明",
        category="账号服务",
        url="https://example.com/support/account",
        status="indexed",
        updatedAt="2026-09-03",
        description="说明账号注册、登录、密码找回和会员权益。",
    ),
    Source(
        id="human-service",
        title="人工客服转接说明",
        category="服务渠道",
        url="https://example.com/support/human",
        status="pending",
        updatedAt="待处理",
        description="说明人工客服入口、服务时间和排队规则。",
    ),
]

faq_items: list[dict] = [
    {
        "id": "return-policy",
        "keywords": ["退货", "退款", "退换货", "无理由"],
        "answer": "根据资料，收到商品后 7 天内可申请无理由退货，商品需保持完好且不影响二次销售。",
        "citations": [
            Citation(
                id="return-cite-1",
                title="退换货政策说明",
                url="https://example.com/support/returns",
                location="退货流程章节",
                snippet="收到商品后 7 天内可申请无理由退货，商品需保持完好且不影响二次销售。",
                score=0.96,
            )
        ],
    },
    {
        "id": "shipping-policy",
        "keywords": ["发货", "物流", "配送", "订单"],
        "answer": "根据资料，现货订单通常在工作日 24 小时内发出，发货后可在订单详情查看物流单号。",
        "citations": [
            Citation(
                id="shipping-cite-1",
                title="订单与物流说明",
                url="https://example.com/support/shipping",
                location="发货时效章节",
                snippet="现货订单通常在工作日 24 小时内发出，发货后可在订单详情查看物流单号。",
                score=0.94,
            )
        ],
    },
    {
        "id": "invoice-policy",
        "keywords": ["发票", "开票", "电子发票"],
        "answer": "根据资料，订单完成后可在个人中心申请电子发票，开票信息需与订单抬头一致。",
        "citations": [
            Citation(
                id="invoice-cite-1",
                title="发票申请说明",
                url="https://example.com/support/invoice",
                location="电子发票章节",
                snippet="订单完成后可在个人中心申请电子发票，开票信息需与订单抬头一致。",
                score=0.92,
            )
        ],
    },
    {
        "id": "human-service",
        "keywords": ["人工客服", "转人工", "人工", "客服"],
        "answer": "根据资料，如需人工客服，可在服务页面选择转人工，服务时间为工作日 9:00-18:00。",
        "citations": [
            Citation(
                id="human-cite-1",
                title="人工客服转接说明",
                url="https://example.com/support/human",
                location="人工服务章节",
                snippet="如需人工客服，可在服务页面选择转人工，服务时间为工作日 9:00-18:00。",
                score=0.9,
            )
        ],
    },
]


def find_mock_answer(question: str) -> dict | None:
    normalized = question.lower().replace(" ", "")

    for item in faq_items:
        if any(
            keyword.lower().replace(" ", "") in normalized
            for keyword in item["keywords"]
        ):
            return item

    return None


def faq_count() -> int:
    return len(faq_items)


def add_faq(
    question: str,
    answer: str,
    keywords: list[str],
    source: str = "人工录入",
) -> dict:
    item = {
        "id": f"faq-{len(faq_items) + 1}",
        "question": question,
        "keywords": keywords or [question],
        "answer": answer,
        "citations": [
            Citation(
                id=f"faq-cite-{len(faq_items) + 1}",
                title=source,
                url="",
                location="FAQ",
                snippet=answer[:200],
                score=1.0,
            )
        ],
    }
    faq_items.append(item)
    return item
