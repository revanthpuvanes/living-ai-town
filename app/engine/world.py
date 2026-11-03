import copy
import hashlib
import json
from typing import Any

RULES_VERSION = 1

LOCATIONS = ("bakery", "school", "shop", "square")

CHARACTERS = {
    "emma": {
        "name": "Emma",
        "profession": "baker",
        "home": "bakery",
    },
    "noah": {
        "name": "Noah",
        "profession": "teacher",
        "home": "school",
    },
    "sophia": {
        "name": "Sophia",
        "profession": "shopkeeper",
        "home": "shop",
    },
}


class InvalidAction(ValueError):
    pass


def initial_state() -> dict[str, Any]:
    return {
        "tick": 0,
        "rules_version": RULES_VERSION,
        "characters": {
            character_id: {
                **details,
                "location": details["home"],
                "activity": "idle",
                "movement": None,
                "money": 100,
                "inventory": {},
            }
            for character_id, details in CHARACTERS.items()
        },
        "locations": {
            location: {"open": True}
            for location in LOCATIONS
        },
    }


def state_hash(state: dict[str, Any]) -> str:
    canonical = json.dumps(
        state,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def validate_move(
    state: dict[str, Any],
    character_id: str,
    destination: str,
    duration_ticks: int,
) -> None:
    if character_id not in state["characters"]:
        raise InvalidAction("Unknown character")

    if destination not in LOCATIONS:
        raise InvalidAction("Unknown destination")

    if type(duration_ticks) is not int or duration_ticks < 1:
        raise InvalidAction("Movement duration must be positive")

    character = state["characters"][character_id]

    if character["movement"] is not None:
        raise InvalidAction("Character is already moving")

    if character["location"] == destination:
        raise InvalidAction("Character is already at destination")


def start_move(
    state: dict[str, Any],
    character_id: str,
    destination: str,
    duration_ticks: int,
) -> dict[str, Any]:
    validate_move(
        state,
        character_id,
        destination,
        duration_ticks,
    )

    updated = copy.deepcopy(state)
    character = updated["characters"][character_id]

    character["movement"] = {
        "from": character["location"],
        "to": destination,
        "start_tick": state["tick"],
        "duration_ticks": duration_ticks,
    }
    character["activity"] = "walking"

    return updated


def advance_tick(state: dict[str, Any]) -> dict[str, Any]:
    updated = copy.deepcopy(state)
    updated["tick"] += 1

    for character in updated["characters"].values():
        movement = character["movement"]

        if movement is None:
            continue

        arrival_tick = (
            movement["start_tick"]
            + movement["duration_ticks"]
        )

        if updated["tick"] >= arrival_tick:
            character["location"] = movement["to"]
            character["movement"] = None
            character["activity"] = "idle"

    return updated
