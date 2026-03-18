from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from sentra import llm as llm_module


class DemoSchema(BaseModel):
    answer: str
    score: float


def test_extract_json_object_handles_markdown_fence() -> None:
    payload = llm_module._extract_json_object(
        "```json\n{\"answer\":\"ok\",\"score\":0.7}\n```"
    )
    assert payload == "{\"answer\":\"ok\",\"score\":0.7}"


def test_provider_name_switches_to_minimax(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.minimax.io/v1")
    assert llm_module.provider_name() == "minimax"


def test_structured_completion_uses_minimax_chat_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "demo")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.minimax.io/v1")
    monkeypatch.setenv("OPENAI_MODEL", "MiniMax-M2.5")
    llm_module.get_client.cache_clear()

    class FakeChatCompletions:
        @staticmethod
        def create(**kwargs):
            assert kwargs["model"] == "MiniMax-M2.5"
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"answer":"ok","score":0.8}')
                    )
                ]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeChatCompletions()))
    monkeypatch.setattr(llm_module, "get_client", lambda: fake_client)

    result = llm_module.structured_completion(
        DemoSchema,
        system_prompt="Return JSON.",
        user_prompt="Say ok.",
    )

    assert result.answer == "ok"
    assert result.score == 0.8
