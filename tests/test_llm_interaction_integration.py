from contextlib import contextmanager
from unittest.mock import patch

import pytest

from app.agents.interactions import run_interactions
from app.llm.client import DialogueGeneration
from app.llm.dialogue import DialogueResponse



@pytest.fixture(autouse=True)
def mock_interaction_lock():
    @contextmanager
    def acquired(*args):
        yield True

    with patch(
        "app.agents.interactions.try_interaction_lock",
        side_effect=acquired,
    ):
        yield


def fake_world():
    return {
        "tick": 9,
        "state_hash": "test-hash",
        "state": {
            "characters": {
                "emma": {
                    "location": "square",
                    "movement": None,
                },
                "noah": {
                    "location": "square",
                    "movement": None,
                },
                "sophia": {
                    "location": "shop",
                    "movement": None,
                },
            }
        },
    }


def test_preview_never_generates():
    with (
        patch(
            "app.agents.interactions.get_world_state",
            return_value=fake_world(),
        ),
        patch(
            "app.agents.interactions.already_spoken_today",
            return_value=False,
        ),
        patch(
            "app.agents.interactions.generate_dialogue",
        ) as generate,
    ):
        results = run_interactions(execute=False)

    generate.assert_not_called()
    assert len(results) == 1
    assert results[0].result is None


def test_mistral_dialogue_is_recorded():
    generation = DialogueGeneration(
        response=DialogueResponse(
            message="How are your students today?",
            emotion="curious",
        ),
        source="mistral",
    )

    with (
        patch(
            "app.agents.interactions.get_world_state",
            return_value=fake_world(),
        ),
        patch(
            "app.agents.interactions.already_spoken_today",
            return_value=False,
        ),
        patch(
            "app.agents.interactions.build_dialogue_context",
        ),
        patch(
            "app.agents.interactions.generate_dialogue",
            return_value=generation,
        ),
        patch(
            "app.agents.interactions.record_conversation",
            return_value={"accepted": True},
        ) as record,
    ):
        results = run_interactions(execute=True)

    assert len(results) == 1
    assert results[0].message == "How are your students today?"
    assert record.call_args.args[3] == (
        "How are your students today?"
    )


def test_fallback_keeps_original_dialogue():
    generation = DialogueGeneration(
        response=DialogueResponse(
            message="Hello Noah!",
            emotion="friendly",
        ),
        source="fallback",
        error="LLM disabled",
    )

    with (
        patch(
            "app.agents.interactions.get_world_state",
            return_value=fake_world(),
        ),
        patch(
            "app.agents.interactions.already_spoken_today",
            return_value=False,
        ),
        patch(
            "app.agents.interactions.build_dialogue_context",
        ),
        patch(
            "app.agents.interactions.generate_dialogue",
            return_value=generation,
        ),
        patch(
            "app.agents.interactions.record_conversation",
            return_value={"accepted": True},
        ) as record,
    ):
        results = run_interactions(execute=True)

    assert len(results) == 1
    assert record.call_args.args[3] == (
        "Good morning, Noah! How are your students?"
    )


def test_cooldown_prevents_generation():
    with (
        patch(
            "app.agents.interactions.get_world_state",
            return_value=fake_world(),
        ),
        patch(
            "app.agents.interactions.already_spoken_today",
            return_value=True,
        ),
        patch(
            "app.agents.interactions.generate_dialogue",
        ) as generate,
    ):
        results = run_interactions(execute=True)

    assert results == []
    generate.assert_not_called()
