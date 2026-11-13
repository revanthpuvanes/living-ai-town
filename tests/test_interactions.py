from app.agents.interactions import find_interactions
from app.engine.world import initial_state


def test_no_interactions_at_workplaces():
    assert find_interactions(initial_state()) == []


def test_emma_and_noah_talk_at_square():
    state = initial_state()
    state["characters"]["emma"]["location"] = "square"
    state["characters"]["noah"]["location"] = "square"

    interactions = find_interactions(state)

    assert len(interactions) == 1
    assert interactions[0][0:2] == ("emma", "noah")


def test_all_three_agents_produce_three_pairs():
    state = initial_state()

    for character in state["characters"].values():
        character["location"] = "square"

    assert len(find_interactions(state)) == 1


def test_moving_character_cannot_talk():
    state = initial_state()
    state["characters"]["emma"]["location"] = "square"
    state["characters"]["noah"]["location"] = "square"
    state["characters"]["emma"]["movement"] = {
        "from": "square",
        "to": "bakery",
        "start_tick": 0,
        "duration_ticks": 3,
    }

    assert find_interactions(state) == []
