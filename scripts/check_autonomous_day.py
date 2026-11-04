from app.agents.scheduler import run_cycle
from app.db.connection import get_connection
from app.db.repository import get_world_state
from app.db.snapshots import verify_replay


def conversation_count():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(*)
                FROM events
                WHERE type = 'CONVERSATION_SPOKEN'
            """)
            return cur.fetchone()[0]


def main():
    before = get_world_state()
    assert before["tick"] == 48, (
        f"Expected tick 48, got {before['tick']}"
    )

    initial_conversations = conversation_count()
    conversations = []

    for _ in range(24):
        result = run_cycle(execute=True)

        assert result.end_tick == result.start_tick + 1

        for interaction in result.interaction_results:
            if interaction.result and interaction.result["accepted"]:
                if not interaction.result["duplicate"]:
                    conversations.append(interaction)

        print(
            f"Tick {result.end_tick}: "
            f"{len(result.interaction_results)} interactions"
        )

    after = get_world_state()
    assert after["tick"] == 72

    print("\n=== AUTONOMOUS CONVERSATIONS ===")
    for conversation in conversations:
        print(
            f"Tick {conversation.tick}: "
            f"{conversation.speaker} -> "
            f"{conversation.listener}: "
            f"{conversation.message}"
        )

    assert len(conversations) >= 1, (
        "No autonomous conversations occurred"
    )

    final_conversations = conversation_count()

    assert (
        final_conversations - initial_conversations
        == len(conversations)
    )

    replay = verify_replay()
    assert (
        replay["full_hash"]
        == replay["snapshot_hash"]
        == replay["live_hash"]
    )

    print("\nFINAL TICK:", after["tick"])
    print("NEW CONVERSATIONS:", len(conversations))
    print("AUTONOMOUS CONVERSATIONS: PASSED")
    print("EVENT REPLAY: PASSED")


if __name__ == "__main__":
    main()
