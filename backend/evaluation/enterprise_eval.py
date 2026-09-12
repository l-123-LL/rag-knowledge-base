from app.evaluation import run_retrieval_evaluation


TOPICS = [
    {
        "id": "return",
        "text": "收到商品后 7 天内可申请无理由退货，商品需保持完好且不影响二次销售。",
        "questions": [
            "退货时间是多久？",
            "几天内可以无理由退货？",
            "商品退货有什么条件？",
            "收到货后还能退吗？",
            "无理由退货需要满足什么？",
        ],
    },
    {
        "id": "shipping",
        "text": "现货订单通常在工作日 24 小时内发出，发货后可在订单详情查看物流单号。",
        "questions": [
            "订单多久发货？",
            "什么时候能发出？",
            "物流单号在哪里看？",
            "现货多久发货？",
            "怎么查物流？",
        ],
    },
    {
        "id": "invoice",
        "text": "订单完成后可在个人中心申请电子发票，开票信息需与订单抬头一致。",
        "questions": [
            "怎么申请发票？",
            "电子发票在哪里开？",
            "发票抬头怎么填？",
            "订单完成后能开票吗？",
            "如何获取电子发票？",
        ],
    },
    {
        "id": "human",
        "text": "如需人工客服，可在服务页面选择转人工，服务时间为工作日 9:00-18:00。",
        "questions": [
            "怎么联系人工客服？",
            "人工客服服务时间？",
            "在哪里转人工？",
            "客服几点上班？",
            "如何找人工？",
        ],
    },
    {
        "id": "address",
        "text": "订单发货前可以在订单详情中修改收货地址，发货后需要联系客服处理。",
        "questions": [
            "怎么修改收货地址？",
            "发货前能改地址吗？",
            "发货后怎么改地址？",
            "订单地址填错了怎么办？",
            "收货地址在哪里修改？",
        ],
    },
    {
        "id": "cancel",
        "text": "订单未发货前可以取消，取消后款项会原路退回。",
        "questions": [
            "怎么取消订单？",
            "未发货能取消吗？",
            "取消订单后多久退款？",
            "订单可以取消吗？",
            "退款退到哪里？",
        ],
    },
    {
        "id": "refund",
        "text": "退款审核通过后通常 1-3 个工作日原路退回，具体到账时间以支付渠道为准。",
        "questions": [
            "退款多久到账？",
            "退款到哪里？",
            "审核通过后多久退款？",
            "退款时间是多久？",
            "钱什么时候退回来？",
        ],
    },
    {
        "id": "member",
        "text": "会员权益在会员中心查看，包含优惠券、积分和专属客服通道。",
        "questions": [
            "会员有什么权益？",
            "会员权益在哪里看？",
            "积分有什么用？",
            "会员有专属客服吗？",
            "优惠券在哪里领？",
        ],
    },
    {
        "id": "coupon",
        "text": "优惠券需在有效期内使用，过期后不可恢复，部分商品不参与优惠券活动。",
        "questions": [
            "优惠券怎么用？",
            "优惠券过期还能用吗？",
            "为什么优惠券不能用？",
            "哪些商品不能用券？",
            "优惠券有效期多久？",
        ],
    },
    {
        "id": "account",
        "text": "忘记密码时可在登录页选择找回密码，通过手机号或邮箱验证后重置。",
        "questions": [
            "忘记密码怎么办？",
            "怎么找回密码？",
            "密码怎么重置？",
            "登录不了怎么办？",
            "手机号可以找回密码吗？",
        ],
    },
]


def build_evaluation_data() -> tuple[list[dict], list[dict]]:
    corpus = [{"id": topic["id"], "text": topic["text"]} for topic in TOPICS]
    questions = [
        {"question": question, "relevant_ids": [topic["id"]]}
        for topic in TOPICS
        for question in topic["questions"]
    ]
    return corpus, questions


def run_enterprise_evaluation() -> dict:
    corpus, questions = build_evaluation_data()
    return run_retrieval_evaluation(corpus, questions)


if __name__ == "__main__":
    import json

    print(json.dumps(run_enterprise_evaluation()["average"], ensure_ascii=False, indent=2))
