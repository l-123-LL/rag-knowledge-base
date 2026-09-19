import json
import os
from typing import Protocol

import httpx


class Judge(Protocol):
    def score(
        self,
        question: str,
        answer: str,
        contexts: list[str],
    ) -> dict[str, float]:
        """返回 faithfulness 和 relevance 分数，范围 0-1。"""


class DeepSeekJudge:
    def __init__(
        self,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        api_key_env: str = "DEEPSEEK_API_KEY",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds

    def score(
        self,
        question: str,
        answer: str,
        contexts: list[str],
    ) -> dict[str, float]:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"缺少环境变量 {self.api_key_env}")

        prompt = (
            "你是客服回答质量评审。请只返回 JSON，不要解释。\n"
            "评分标准（rubric）：\n"
            "- faithfulness（答案是否有资料依据）："
            "1.0 = 每一句都能在资料里找到依据；"
            "0.5 = 主要结论有依据，但夹带了资料里没有的细节；"
            "0.0 = 关键结论在资料里找不到，属于编造。\n"
            "- relevance（是否回答了用户的问题）："
            "1.0 = 直接回答了问题；"
            "0.5 = 只答了一部分或答得含糊；"
            "0.0 = 答非所问或只是拒答。\n"
            "请严格按上述档位给分，不要给中间随意值。\n"
            '返回格式：{"faithfulness": <0|0.5|1>, "relevance": <0|0.5|1>}\n'
            f"问题：{question}\n"
            f"答案：{answer}\n"
            f"资料：{chr(10).join(contexts) if contexts else '（无检索资料）'}"
        )

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()

        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        scores = json.loads(content)
        return {
            "faithfulness": float(scores.get("faithfulness", 0.0)),
            "relevance": float(scores.get("relevance", 0.0)),
        }
