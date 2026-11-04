import io
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
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "message": "Hello Noah!",
                        "emotion": "friendly",
                    })
                }
            }]
        }).encode()


def test_budget_exhaustion_blocks_network(monkeypatch):
    monkeypatch.setenv("AI_TOWN_ENABLE_LLM", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    def forbidden(*args, **kwargs):
        raise AssertionError("Network must not be called")

    with patch(
        "app.llm.client.reserve_llm_request",
        return_value=False,
    ) as reserve:
        result = generate_dialogue(
            context(),
            transport=forbidden,
        )

    reserve.assert_called_once()
    assert result.source == "fallback"
    assert result.error == "LLM request budget exhausted"


def test_success_reserves_exactly_once(monkeypatch):
    monkeypatch.setenv("AI_TOWN_ENABLE_LLM", "1")
    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")

    with patch(
        "app.llm.client.reserve_llm_request",
        return_value=True,
    ) as reserve:
        result = generate_dialogue(
            context(),
            transport=lambda req, timeout: FakeResponse(),
        )

    reserve.assert_called_once()
    assert result.source == "mistral"


def test_disabled_client_does_not_reserve(monkeypatch):
    monkeypatch.delenv("AI_TOWN_ENABLE_LLM", raising=False)

    with patch(
        "app.llm.client.reserve_llm_request",
    ) as reserve:
        result = generate_dialogue(context())

    reserve.assert_not_called()
    assert result.source == "fallback"
