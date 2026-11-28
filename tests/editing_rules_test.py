import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "video-agent"))
from agent import cadence, clips, looks

# cadence: no gap longer than MAX_GAP, pulses land on word ends
words = [{"end": float(x)} for x in range(1, 9)]
ev = sorted([0.0, *cadence.fill([], 9.0, words), 9.0])
assert all(b - a <= cadence.MAX_GAP + 0.01 for a, b in zip(ev, ev[1:])), ev
assert all(t in {w["end"] for w in words} for t in cadence.fill([], 9.0, words))
assert cadence.fill([], 2.0, None) == [] and cadence.fill([1.0, 3.0, 5.0], 6.0, None) == []

# cuts fall on word ends, are at least 0.8 s apart, never inside a word
cp = clips.cut_points([{"end": 1.0}, {"end": 2.1}, {"end": 3.0}], 120, 30, 3)
assert cp == [0, 30, 90, 120], cp
assert clips.cut_points(None, 90, 30, 3) == [0, 30, 60, 90]
assert clips.cut_points([{"end": 1.0}], 90, 30, 1) == [0, 90]

# transitions: settle only on scene 1, punchy beats arrive with motion, never the same twice in a row
look = {"transitions": "mixed"}
prev, seen = None, []
for i, b in enumerate(["pain", "poke", "fix", "payoff", "rehook", "recap", "cta"]):
    t = looks.pick_transition({"beat": b, "transition": "settle"}, i, look, {}, prev)
    assert (t == "settle") == (i == 0) and t != prev, (i, t)
    if b in ("poke", "rehook", "cta"):
        assert t in looks.PUNCHY, (b, t)
    prev = t
assert looks.pick_transition({"transition": "iris", "beat": "fix"}, 3, look, {}, "zoom") == "iris"
print("editing rules ok")

# the compulsory trio: a real proof, an exploding caption, a word behind his head
from agent import avatar, effects_rule as er, proof

sc = [{"beat": b, "narration": "x " * 6} for b in ("pain", "poke", "fix", "payoff", "cta")]
assert er.ensure_proof(sc, None) is None and not er.proof_indices(sc)
note = er.ensure_proof(sc, "hotel")
assert note and er.proof_indices(sc) == {3}, note       # the payoff scene (nearest the 60% mark) becomes the proof
assert er.ensure_proof(sc, "hotel") is None             # one is enough
assert er.explode_slot(["pain", "poke", "rehook", "cta"], [True] * 4) == 2
assert er.explode_slot(["pain", "poke", "fix", "cta"], [True] * 4, {1}) == 2 and er.explode_slot(["a", "b"], [True] * 2) is None
caps = er.caption_plan([True, True, True, True], "pill", "s", er.explode_slot(["pain", "poke", "fix", "cta"], [True] * 4))
assert caps.count("explode") == 1 and caps[1] == "explode", caps
cuts = [{"f": 0, "n": 100, "frame": "full", "alpha": True}]
w = avatar.behind_word("Most customers search before they call", cuts, 100)
assert w and w["text"] == "SEARCH", w      # short and punchy: 4-8 letters
assert avatar.behind_word("Hello there", [{"f": 0, "n": 100, "frame": "none", "alpha": True}], 100) is None
assert avatar.behind_word("Hello there", [{"f": 0, "n": 100, "frame": "full"}], 100) is None
assert proof.pick("x") is None or isinstance(proof.pick("x"), str)
print("trio ok")
