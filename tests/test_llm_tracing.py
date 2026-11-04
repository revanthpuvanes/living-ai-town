import json
from unittest.mock import patch

from app.llm.client import generate_dialogue
from app.llm.context import AGENT_PROFILES, DialogueContext


def context():
    return DialogueContext(
        speaker_id="emma",
        listener_id="noah",
        tick=57,
        location="square",
        speaker_profile=AGENT_PROFILES["emma"],
        listener_profile=AGENT_PROFILES["noah"],
        recent_conversations=(),
    )


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return json.dumps({
            "model": "mistral-small-test-version",
            "usage": {
                "prompt_tokens": 80,
                "completion_tokens": 25,
                "total_tokens": 105,
            },
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "message": "Hello Noah!",
                        "emotion": "friendly",
                    })
                }
            }],
        }).encode()


def test_successful_generation_has_trace(monkeypatch):
    monkeypatch.setenv("AI_TOWN_ENABLE_LLM", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    with patch(
        "app.llm.client.reserve_llm_request",
        return_value=True,
    ):
        result = generate_dialogue(
            context(),
            transport=lambda req, timeout: FakeResponse(),
        )

    assert result.source == "mistral"
    assert result.model == "mistral-small-test-version"
    assert result.prompt_tokens == 80
    assert result.completion_tokens == 25
    assert result.total_tokens == 105
    assert result.latency_ms is not None
    assert result.latency_ms >= 0


def test_fallback_does_not_invent_usage(monkeypatch):
    monkeypatch.setenv("AI_TOWN_ENABLE_LLM", "0")

    result = generate_dialogue(context())

    assert result.source == "fallback"
    assert result.model is None
    assert result.prompt_tokens is None
    assert result.total_tokens is None


def test_timeout_has_latency_but_no_fake_tokens(monkeypatch):
    monkeypatch.setenv("AI_TOWN_ENABLE_LLM", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    def timeout(req, timeout):
        raise TimeoutError("Simulated timeout")

    with patch(
        "app.llm.client.reserve_llm_request",
        return_value=True,
    ):
        result = generate_dialogue(
            context(),
            transport=timeout,
        )

    assert result.source == "fallback"
    assert result.error == "TimeoutError"
    assert result.latency_ms is not None
    assert result.total_tokens is None
