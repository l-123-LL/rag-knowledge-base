import os
from typing import Protocol

import httpx

from .retrieval import RetrievedChunk


class GenerationError(RuntimeError):
    """生成失败时抛出，方便接口层统一返回错误。"""


class Generator(Protocol):
    def generate(self, question: str, contexts: list[RetrievedChunk]) -> str:
        """根据问题和检索片段生成答案。"""


class DeepSeekGenerator:
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

    def generate(self, question: str, contexts: list[RetrievedChunk]) -> str:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise GenerationError(f"缺少环境变量 {self.api_key_env}")

        system_prompt = (
            "你是面向医务人员的医学知识助手。"
            "只能根据提供的资料回答，不得编造。"
            "如果资料不足，请明确说明资料不足。"
            "回答要给出结论、依据，并尽量引用来源。"
        )
        context_text = "\n\n".join(
            f"[来源：{chunk.metadata.get('source', '未知来源')}]\n{chunk.text}"
            for chunk in contexts
        )
        user_prompt = f"资料：\n{context_text}\n\n问题：{question}"

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()

        payload = response.json()
        return payload["choices"][0]["message"]["content"]
