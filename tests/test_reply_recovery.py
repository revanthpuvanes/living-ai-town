from unittest.mock import patch

from app.agents.replies import process_reply


def opening():
    return {
        "event_id": 123,
        "tick": 57,
        "speaker": "emma",
        "listener": "noah",
        "message": "Hello Noah!",
        "location": "square",
    }


def test_existing_reply_skips_generation():
    with (
        patch(
            "app.agents.replies.try_interaction_lock"
        ) as lock,
        patch(
            "app.agents.replies.reply_exists",
            return_value=True,
        ),
        patch(
            "app.agents.replies.generate_dialogue"
        ) as generate,
    ):
        lock.return_value.__enter__.return_value = True
        assert process_reply(opening()) is None

    generate.assert_not_called()


def test_unavailable_lock_skips_generation():
    with (
        patch(
            "app.agents.replies.try_interaction_lock"
        ) as lock,
        patch(
            "app.agents.replies.generate_dialogue"
        ) as generate,
    ):
        lock.return_value.__enter__.return_value = False
        assert process_reply(opening()) is None

    generate.assert_not_called()


def test_moving_character_skips_reply():
    world = {
        "tick": 58,
        "state_hash": "test-hash",
        "state": {
            "characters": {
                "emma": {
                    "location": "square",
                    "movement": None,
                },
                "noah": {
                    "location": "square",
                    "movement": {"to": "school"},
                },
            },
        },
    }

    with (
        patch(
            "app.agents.replies.try_interaction_lock"
        ) as lock,
        patch(
            "app.agents.replies.reply_exists",
            return_value=False,
        ),
        patch(
            "app.agents.replies.get_world_state",
            return_value=world,
        ),
        patch(
            "app.agents.replies.generate_dialogue"
        ) as generate,
    ):
        lock.return_value.__enter__.return_value = True
        assert process_reply(opening()) is None

    generate.assert_not_called()
