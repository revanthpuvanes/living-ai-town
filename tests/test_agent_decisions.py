import pytest

from app.agents.decisions import (
    AgentObservation,
    DeterministicAgent,
)


@pytest.fixture
def agent():
    return DeterministicAgent()


@pytest.mark.parametrize(
    ("character", "destination"),
    [
        ("emma", "bakery"),
        ("noah", "school"),
        ("sophia", "shop"),
    ],
)
def test_idle_agent_moves_to_workplace(agent, character, destination):
    decision = agent.decide(
        AgentObservation(
            character_id=character,
            location="home",
            activity="idle",
            current_tick=0,
        )
    )

    assert decision.action == "MOVE"
    assert decision.destination == destination
    assert decision.duration_ticks == 3


def test_agent_waits_at_workplace(agent):
    decision = agent.decide(
        AgentObservation(
            character_id="emma",
            location="bakery",
            activity="idle",
            current_tick=3,
        )
    )

    assert decision.action == "WAIT"


def test_agent_waits_while_busy(agent):
    decision = agent.decide(
        AgentObservation(
            character_id="emma",
            location="home",
            activity="moving",
            current_tick=1,
        )
    )

    assert decision.action == "WAIT"


def test_unknown_character_rejected(agent):
    with pytest.raises(ValueError):
        agent.decide(
            AgentObservation(
                character_id="unknown",
                location="home",
                activity="idle",
                current_tick=0,
            )
        )
