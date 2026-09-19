import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

import httpx

from .retrieval import RetrievedChunk


class GenerationError(RuntimeError):
    """生成失败时抛出，方便接口层统一返回错误。"""


@dataclass
class GenerationResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Generator(Protocol):
    def generate(
        self,
        question: str,
        contexts: list[RetrievedChunk],
        history: list[dict] | None = None,
    ) -> GenerationResult:
        """根据问题和检索片段生成答案及用量信息。"""

    def stream(
        self,
        question: str,
        contexts: list[RetrievedChunk],
        history: list[dict] | None = None,
    ) -> Iterator[str]:
        """流式返回生成内容。"""


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

    def generate(
        self,
        question: str,
        contexts: list[RetrievedChunk],
        history: list[dict] | None = None,
    ) -> GenerationResult:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise GenerationError(f"缺少环境变量 {self.api_key_env}")

        system_prompt = (
            "你是企业智能客服助手。"
            "只能根据提供的知识库资料回答，不得编造。"
            "如果资料不足，请说明无法确认，并引导用户联系人工客服。"
            "回答要简洁、专业、友好，并尽量引用来源。"
        )
        context_text = "\n\n".join(
            f"[来源：{chunk.metadata.get('source', '未知来源')}]\n{chunk.text}"
            for chunk in contexts
        )
        user_prompt = f"资料：\n{context_text}\n\n问题：{question}"
        messages = [
            {"role": "system", "content": system_prompt},
            *(history or []),
            {"role": "user", "content": user_prompt},
        ]

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()

        payload = response.json()
        usage = payload.get("usage", {})
        return GenerationResult(
            text=payload["choices"][0]["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )

    def stream(
        self,
        question: str,
        contexts: list[RetrievedChunk],
        history: list[dict] | None = None,
    ) -> Iterator[str]:
        api_key = os.getenv(self.api_key_env)
        if not api_key:
            raise GenerationError(f"缺少环境变量 {self.api_key_env}")

        system_prompt = (
            "你是企业智能客服助手。"
            "只能根据提供的知识库资料回答，不得编造。"
            "如果资料不足，请说明无法确认，并引导用户联系人工客服。"
        )
        context_text = "\n\n".join(
            f"[来源：{chunk.metadata.get('source', '未知来源')}]\n{chunk.text}"
            for chunk in contexts
        )
        user_prompt = f"资料：\n{context_text}\n\n问题：{question}"
        messages = [
            {"role": "system", "content": system_prompt},
            *(history or []),
            {"role": "user", "content": user_prompt},
        ]

        with httpx.Client(timeout=None) as client, client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
                "stream": True,
            },
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                payload = json.loads(data)
                delta = payload["choices"][0]["delta"].get("content")
                if delta:
                    yield delta
