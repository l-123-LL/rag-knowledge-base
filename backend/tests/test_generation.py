import pytest

from app.generation import DeepSeekGenerator, GenerationError


def test_deepseek_generator_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    generator = DeepSeekGenerator(api_key_env="DEEPSEEK_API_KEY")

    with pytest.raises(GenerationError, match="DEEPSEEK_API_KEY"):
        generator.generate("问题", [])
