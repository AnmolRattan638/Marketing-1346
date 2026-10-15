"""Offline test: Buffer posts must publish now (shareNow), never wait in the Buffer queue."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import buffer

seen = []
def ok(q):
    seen.append(q)
    return {"createPost": {"post": {"id": "p1", "dueAt": "now"}}}
buffer._gql = ok
assert buffer.create_post("c", "hi", "https://x/y.jpg")["id"] == "p1"
assert "mode: shareNow" in seen[0] and "addToQueue" not in seen[0] and "assets" in seen[0], seen[0]

seen.clear()
def no_sharenow(q):
    seen.append(q)
    if "shareNow" in q:
        raise RuntimeError("Value 'shareNow' does not exist in enum")
    return {"createPost": {"post": {"id": "p2", "dueAt": "2026-01-01T00:02:00.000Z"}}}
buffer._gql = no_sharenow
assert buffer.create_post("c", "hi")["id"] == "p2"
assert len(seen) == 2 and "customScheduled" in seen[1] and "dueAt:" in seen[1] and "addToQueue" not in seen[1], seen

def always_error(q):
    return {"createPost": {"message": "channel disconnected"}}
buffer._gql = always_error
try:
    buffer.create_post("c", "hi"); raise SystemExit("should have failed")
except RuntimeError as e:
    assert "channel disconnected" in str(e)
print("buffer test passed: shareNow first, customScheduled fallback, never addToQueue, errors surface")
