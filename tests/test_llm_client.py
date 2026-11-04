import io
import json
from unittest.mock import patch

from app.llm.client import (
    MAX_OUTPUT_TOKENS,
    generate_dialogue,
)
from app.llm.context import AGENT_PROFILES, DialogueContext



import pytest


@pytest.fixture(autouse=True)
def mock_request_budget():
    with patch(
        "app.llm.client.reserve_llm_request",
        return_value=True,
    ):
        yield

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
    def __init__(self, content):
        self.data = io.BytesIO(json.dumps({
            "choices": [{
                "message": {"content": content}
            }]
        }).encode())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        return self.data.read(size)


def test_disabled_does_not_call_network(monkeypatch):
    monkeypatch.delenv("AI_TOWN_ENABLE_LLM", raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("Network should not be called")

    result = generate_dialogue(context(), transport=forbidden)

    assert result.source == "fallback"


def test_missing_key_falls_back(monkeypatch):
    monkeypatch.setenv("AI_TOWN_ENABLE_LLM", "1")
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    result = generate_dialogue(context())
    assert result.source == "fallback"


def test_valid_model_response(monkeypatch):
    monkeypatch.setenv("AI_TOWN_ENABLE_LLM", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    def fake_transport(req, timeout):
        body = json.loads(req.data)
        assert body["max_tokens"] == MAX_OUTPUT_TOKENS
        assert timeout == 8

        return FakeResponse(json.dumps({
            "message": "Good morning, Noah!",
            "emotion": "friendly",
        }))

    result = generate_dialogue(
        context(),
        transport=fake_transport,
    )

    assert result.source == "mistral"
    assert result.response.message == "Good morning, Noah!"


def test_invalid_model_response_falls_back(monkeypatch):
    monkeypatch.setenv("AI_TOWN_ENABLE_LLM", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    def fake_transport(req, timeout):
        return FakeResponse("invalid json")

    result = generate_dialogue(
        context(),
        transport=fake_transport,
    )

    assert result.source == "fallback"


def test_network_failure_falls_back(monkeypatch):
    monkeypatch.setenv("AI_TOWN_ENABLE_LLM", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    def broken_transport(req, timeout):
        raise TimeoutError("simulated timeout")

    result = generate_dialogue(
        context(),
        transport=broken_transport,
    )

    assert result.source == "fallback"
    assert result.error == "TimeoutError"
