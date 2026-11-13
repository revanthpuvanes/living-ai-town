from dataclasses import dataclass
from typing import Literal


HOME_LOCATIONS = {
    "emma": "bakery",
    "noah": "school",
    "sophia": "shop",
}

CYCLE_LENGTH = 24

# The desired destination for each character in each phase.
ROUTINES = {
    "emma": (
        (0, "bakery"),
        (6, "square"),
        (12, "bakery"),
    ),
    "noah": (
        (0, "school"),
        (6, "square"),
        (12, "school"),
    ),
    "sophia": (
        (0, "shop"),
        (6, "square"),
        (12, "shop"),
    ),
}


@dataclass(frozen=True)
class AgentObservation:
    character_id: str
    location: str
    activity: str
    current_tick: int
    state_hash: str | None = None


@dataclass(frozen=True)
class AgentDecision:
    action: Literal["MOVE", "WAIT"]
    character_id: str
    destination: str | None
    duration_ticks: int | None
    reason: str


def scheduled_destination(character_id: str, tick: int) -> str:
    if character_id not in ROUTINES:
        raise ValueError(f"Unknown character: {character_id}")

    phase = tick % CYCLE_LENGTH
    destination = HOME_LOCATIONS[character_id]

    for start_tick, location in ROUTINES[character_id]:
        if phase >= start_tick:
            destination = location

    return destination


class DeterministicAgent:
    def decide(self, observation: AgentObservation) -> AgentDecision:
        character_id = observation.character_id

        destination = scheduled_destination(
            character_id,
            observation.current_tick,
        )

        if observation.activity != "idle":
            return AgentDecision(
                action="WAIT",
                character_id=character_id,
                destination=None,
                duration_ticks=None,
                reason="Character is busy",
            )

        if observation.location == destination:
            return AgentDecision(
                action="WAIT",
                character_id=character_id,
                destination=None,
                duration_ticks=None,
                reason="Character is at scheduled destination",
            )

        return AgentDecision(
            action="MOVE",
            character_id=character_id,
            destination=destination,
            duration_ticks=3,
            reason=f"Follow daily routine to {destination}",
        )
