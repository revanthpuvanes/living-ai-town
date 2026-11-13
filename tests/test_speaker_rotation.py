from app.agents.interactions import find_interactions


def test_speaker_rotation_by_day():
    state = {
        "characters": {
            character: {
                "location": "square",
                "movement": None,
            }
            for character in ("emma", "noah", "sophia")
        }
    }

    expected_pairs = [
        {"emma", "noah"},
        {"noah", "sophia"},
        {"sophia", "emma"},
        {"emma", "noah"},
    ]

    for day, expected in enumerate(expected_pairs):
        interactions = find_interactions(state, tick=day * 24)
        assert len(interactions) == 1
        assert set(interactions[0][:2]) == expected
