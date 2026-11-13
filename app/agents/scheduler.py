from app.db.visitor_replies import reply_to_pending_visitors
from dataclasses import dataclass
from uuid import UUID, uuid5

from app.agents.decisions import DeterministicAgent
from app.agents.interactions import run_interactions
from app.agents.replies import process_reply
from app.db.conversations import get_pending_auto_replies
from app.agents.observations import observe_character
from app.agents.runner import run_agent_once
from app.db.scheduler_lock import try_scheduler_lock
from app.db.idempotent_ticks import advance_tick_once
from app.db.repository import get_world_state


AGENT_IDS = ("emma", "noah", "sophia")

SCHEDULER_NAMESPACE = UUID(
    "72a86c15-3cf0-4c21-a7bd-c6b75a709f26"
)


@dataclass(frozen=True)
class CycleResult:
    start_tick: int
    end_tick: int
    agent_results: tuple
    tick_result: dict | None
    interaction_results: tuple = ()


def preview_cycle():
    results = []

    for agent_id in AGENT_IDS:
        observation = observe_character(agent_id)
        decision = DeterministicAgent().decide(observation)

        results.append({
            "agent": agent_id,
            "tick": observation.current_tick,
            "action": decision.action,
            "destination": decision.destination,
            "reason": decision.reason,
        })

    return results


def run_cycle(*, execute: bool = False):
    if execute:
        with try_scheduler_lock() as acquired:
            if not acquired:
                raise RuntimeError(
                    "Another scheduler cycle is already running"
                )
            return _run_cycle_impl(execute=True)

    return _run_cycle_impl(execute=False)


def _run_cycle_impl(*, execute: bool):
    before = get_world_state()
    start_tick = before["tick"]

    if not execute:
        return CycleResult(
            start_tick=start_tick,
            end_tick=start_tick,
            agent_results=tuple(preview_cycle()),
            tick_result=None,
            interaction_results=tuple(
                run_interactions(execute=False)
            ),
        )

    # Respond to pending visitor messages.
    reply_to_pending_visitors(limit=5)

    # Recover unfinished replies before characters move.
    for opening in get_pending_auto_replies(start_tick):
        process_reply(opening)

    # Start new conversations while characters are together.
    interactions = tuple(
        run_interactions(execute=True)
    )

    # Complete newly opened conversations before movement.
    for opening in get_pending_auto_replies(start_tick):
        process_reply(opening)

    # Then let each character make a movement decision.
    results = []
    for agent_id in AGENT_IDS:
        results.append(run_agent_once(agent_id))

    # Advance one simulated tick.
    tick_request_id = uuid5(
        SCHEDULER_NAMESPACE,
        f"scheduler-tick-{start_tick + 1}",
    )
    tick_result = advance_tick_once(tick_request_id)

    after = get_world_state()

    return CycleResult(
        start_tick=start_tick,
        end_tick=after["tick"],
        agent_results=tuple(results),
        tick_result=tick_result,
        interaction_results=interactions,
    )
