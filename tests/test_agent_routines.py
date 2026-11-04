import pytest

from app.agents.decisions import (
    AgentObservation,
    DeterministicAgent,
    scheduled_destination,
)


@pytest.mark.parametrize(
    "agent,tick,destination",
    [
        ("emma", 0, "bakery"),
        ("emma", 6, "square"),
        ("emma", 12, "bakery"),
        ("emma", 24, "bakery"),
        ("noah", 5, "school"),
        ("noah", 6, "square"),
        ("noah", 18, "school"),
        ("sophia", 11, "shop"),
        ("sophia", 12, "square"),
        ("sophia", 24, "shop"),
    ],
)
def test_scheduled_destination(agent, tick, destination):
    assert scheduled_destination(agent, tick) == destination


def test_emma_moves_to_square():
    observation = AgentObservation(
        character_id="emma",
        location="bakery",
        activity="idle",
        current_tick=30,
    )
    decision = DeterministicAgent().decide(observation)
    assert decision.action == "MOVE"
    assert decision.destination == "square"
    assert decision.duration_ticks == 3


def test_busy_character_waits():
    observation = AgentObservation(
        character_id="emma",
        location="bakery",
        activity="walking",
        current_tick=30,
    )
    decision = DeterministicAgent().decide(observation)
    assert decision.action == "WAIT"


def test_unknown_character_rejected():
    with pytest.raises(ValueError):
        scheduled_destination("unknown", 0)
