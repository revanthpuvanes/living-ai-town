from dataclasses import replace

from app.llm.context import DialogueContext
from app.llm.prompts import build_dialogue_messages


def test_reply_prompt_includes_opening_message():
    context = DialogueContext(
        speaker_id="noah",
        listener_id="emma",
        tick=57,
        location="square",
        speaker_profile={
            "name": "Noah",
            "role": "teacher",
            "workplace": "school",
            "personality": "thoughtful",
        },
        listener_profile={
            "name": "Emma",
            "role": "baker",
            "workplace": "bakery",
            "personality": "warm",
        },
        recent_conversations=(),
    )

    messages = build_dialogue_messages(
        context,
        reply_to="Emma, would you like to help with the school fair?",
    )

    assert "Emma, would you like to help with the school fair?" in (
        messages[1]["content"]
    )
    assert "reply" in messages[1]["content"].lower()
