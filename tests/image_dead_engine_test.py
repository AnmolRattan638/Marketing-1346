import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src.agents import image


def _boom(prompt, path):
    raise RuntimeError("402 Client Error: Payment Required")


def _ok(prompt, path):
    return None


image._DEAD.clear()
assert image._dead(_boom, RuntimeError("402 Payment Required")) and "boom" in image._DEAD    # out of credit: skipped for the rest of the run
assert not image._dead(_ok, RuntimeError("timeout")) and "ok" not in image._DEAD            # a timeout is retried normally
assert "boom" not in [e.__name__.strip("_") for e in image._engines()]
print("dead engine test passed")
