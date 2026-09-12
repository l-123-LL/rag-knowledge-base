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
            "请评估客服回答质量，只返回 JSON，不要解释。\n"
            "faithfulness：答案是否完全基于资料，1 表示完全有依据。\n"
            "relevance：答案是否直接回答用户问题，1 表示完全相关。\n"
            f"问题：{question}\n"
            f"答案：{answer}\n"
            f"资料：{chr(10).join(contexts)}"
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
