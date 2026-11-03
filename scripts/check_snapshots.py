from app.db.snapshots import create_snapshot, verify_replay
from app.db.simulation import advance_world_tick

print("=== CREATE SNAPSHOT ===")
snapshot = create_snapshot()
print(snapshot)

print("\n=== ADVANCE TWO TICKS ===")
for _ in range(2):
    print(advance_world_tick())

print("\n=== VERIFY BOTH REPLAY PATHS ===")
result = verify_replay()

for key, value in result.items():
    print(f"{key}: {value}")

assert result["full_hash"] == result["snapshot_hash"]
assert result["snapshot_hash"] == result["live_hash"]

print("\nSNAPSHOT REPLAY: PASSED")
