from app.agents.decisions import AgentObservation
from app.db.repository import get_world_state


def observe_character(character_id: str) -> AgentObservation:
    """
    Build a grounded agent observation from PostgreSQL.

    Read-only: does not create decisions or advance ticks.
    """
    world = get_world_state()
    characters = world["state"]["characters"]

    if character_id not in characters:
        raise ValueError(f"Unknown character: {character_id}")

    character = characters[character_id]

    activity = character["activity"]

    if character["movement"] is not None:
        activity = "walking"

    return AgentObservation(
        character_id=character_id,
        location=character["location"],
        activity=activity,
        current_tick=world["tick"],
        state_hash=world["state_hash"],
    )
