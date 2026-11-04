from app.agents.decisions import DeterministicAgent
from app.agents.observations import observe_character


def main():
    agent = DeterministicAgent()

    for character_id in ("emma", "noah", "sophia"):
        observation = observe_character(character_id)
        decision = agent.decide(observation)

        print(f"\nAGENT: {character_id}")
        print(f"  Tick: {observation.current_tick}")
        print(f"  Location: {observation.location}")
        print(f"  Activity: {observation.activity}")
        print(f"  Decision: {decision.action}")
        print(f"  Destination: {decision.destination}")
        print(f"  Reason: {decision.reason}")

    print("\nAGENT OBSERVATIONS: PASSED")


if __name__ == "__main__":
    main()
