from dataclasses import dataclass
from uuid import UUID, uuid5

from app.agents.decisions import DeterministicAgent
from app.agents.observations import observe_character
from app.db.repository import record_move


ACTION_NAMESPACE = UUID("bfdbda5b-65b7-49e4-93e9-78a28287fd02")


@dataclass(frozen=True)
class AgentRunResult:
    character_id: str
    action: str
    result: dict


def run_agent_once(character_id: str) -> AgentRunResult:
    """
    Observe -> decide -> execute one agent action.

    A deterministic action ID makes retries of the same
    observation and decision idempotent.
    """
    observation = observe_character(character_id)
    decision = DeterministicAgent().decide(observation)

    if decision.action == "WAIT":
        return AgentRunResult(
            character_id=character_id,
            action="WAIT",
            result={"reason": decision.reason},
        )

    if decision.action != "MOVE":
        raise ValueError(f"Unsupported action: {decision.action}")

    if decision.destination is None or decision.duration_ticks is None:
        raise ValueError("MOVE requires destination and duration")

    if observation.state_hash is None:
        raise ValueError("Observation is missing state hash")

    action_key = (
        f"{observation.state_hash}:"
        f"{observation.current_tick}:"
        f"{decision.character_id}:"
        f"{decision.action}:"
        f"{decision.destination}:"
        f"{decision.duration_ticks}"
    )
    action_id = uuid5(ACTION_NAMESPACE, action_key)

    result = record_move(
        action_id=action_id,
        character_id=decision.character_id,
        destination=decision.destination,
        duration_ticks=decision.duration_ticks,
        expected_tick=observation.current_tick,
        expected_state_hash=observation.state_hash,
    )

    return AgentRunResult(
        character_id=character_id,
        action=decision.action,
        result=result,
    )
