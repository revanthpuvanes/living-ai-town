import json
import os
import time
from dataclasses import dataclass
from urllib import error, request

from app.llm.budget import reserve_llm_request
from app.llm.dialogue import (
    DialogueResponse,
    InvalidDialogue,
    validate_dialogue,
)
from app.llm.prompts import build_dialogue_messages


MISTRAL_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MODEL = "mistral-small-latest"
MAX_OUTPUT_TOKENS = 120
REQUEST_TIMEOUT_SECONDS = 8


@dataclass(frozen=True)
class DialogueGeneration:
    response: DialogueResponse
    source: str
    error: str | None = None
    model: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    latency_ms: float | None = None


def fallback_dialogue(context):
    listener = context.listener_profile["name"]

    return DialogueResponse(
        message=(
            f"Hello {listener}! It's good to see you "
            f"here at the {context.location}."
        ),
        emotion="friendly",
    )


def generate_dialogue(context, *, transport=None):
    fallback = fallback_dialogue(context)

    if os.getenv("AI_TOWN_ENABLE_LLM") != "1":
        return DialogueGeneration(
            response=fallback,
            source="fallback",
            error="LLM disabled",
        )

    api_key = os.getenv("MISTRAL_API_KEY")

    if not api_key:
        return DialogueGeneration(
            response=fallback,
            source="fallback",
            error="Missing Mistral API key",
        )

    body = {
        "model": DEFAULT_MODEL,
        "messages": build_dialogue_messages(context),
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": 0.5,
        "response_format": {"type": "json_object"},
    }

    sender = transport or request.urlopen
    start = time.perf_counter()

    try:
        if not reserve_llm_request():
            return DialogueGeneration(
                response=fallback,
                source="fallback",
                error="LLM request budget exhausted",
            )

        req = request.Request(
            MISTRAL_ENDPOINT,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with sender(
            req,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            raw = response.read(65537)

        result = json.loads(raw)

        content = result["choices"][0]["message"]["content"]
        dialogue = validate_dialogue(content)

        usage = result.get("usage") or {}

        latency_ms = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        return DialogueGeneration(
            response=dialogue,
            source="mistral",
            model=result.get("model"),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            latency_ms=latency_ms,
        )

    except (
        error.URLError,
        TimeoutError,
        OSError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        InvalidDialogue,
    ) as exc:
        return DialogueGeneration(
            response=fallback,
            source="fallback",
            error=type(exc).__name__,
            latency_ms=round(
                (time.perf_counter() - start) * 1000,
                2,
            ),
        )
