from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel


class LLMConfigError(RuntimeError):
    """Raised when LLM functionality is requested without valid configuration."""


class LLMResponseError(RuntimeError):
    """Raised when the model does not return a parseable structured response."""


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


def llm_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def default_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def base_url() -> str:
    return os.getenv("OPENAI_BASE_URL", "")


def provider_name() -> str:
    url = base_url().lower()
    if "minimax" in url:
        return "minimax"
    return "openai"


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMConfigError("OPENAI_API_KEY is not set")

    base_url = os.getenv("OPENAI_BASE_URL")
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def structured_completion(
    schema: type[StructuredModel],
    *,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
) -> StructuredModel:
    if provider_name() == "minimax":
        return _structured_completion_minimax_chat(
            schema,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
        )

    return _structured_completion_openai_responses(
        schema,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
    )


def _structured_completion_openai_responses(
    schema: type[StructuredModel],
    *,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
) -> StructuredModel:
    client = get_client()
    response = client.responses.parse(
        model=model or default_model(),
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        text_format=schema,
    )
    parsed = response.output_parsed
    if parsed is None:
        raise LLMResponseError("OpenAI response did not contain parsed structured output")
    return parsed


def _structured_completion_minimax_chat(
    schema: type[StructuredModel],
    *,
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
) -> StructuredModel:
    client = get_client()
    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=True)
    response = client.chat.completions.create(
        model=model or default_model(),
        messages=[
            {
                "role": "system",
                "content": (
                    f"{system_prompt}\n\n"
                    "Return only valid JSON that conforms to this JSON Schema. "
                    "Do not include markdown fences or extra commentary.\n"
                    f"JSON Schema:\n{schema_json}"
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        extra_body={"reasoning_split": True},
    )
    message = response.choices[0].message
    content = _coerce_message_content(message.content)
    payload = _extract_json_object(content)
    try:
        return schema.model_validate_json(payload)
    except Exception as exc:
        raise LLMResponseError(f"MiniMax response did not match schema: {exc}") from exc


def _coerce_message_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        if chunks:
            return "".join(chunks)
    raise LLMResponseError("Model response did not contain text content")


def _extract_json_object(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise LLMResponseError("Could not locate a JSON object in model output")
    return cleaned[start : end + 1]
