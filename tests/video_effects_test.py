"""Offline test: every reel uses >= 4 different animation styles and >= 3 different caption styles, and every effect plays one of the custom sounds."""
import os, pathlib, sys
REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "video-agent"))
os.chdir(REPO / "video-agent")
from agent import effects_rule as er, graphics, sfxcustom

assert len(graphics.EFFECTS) == 14 and set(graphics.EFFECTS) <= set(graphics.MOCKS) and set(graphics.EFFECTS) == set(sfxcustom.EFFECT_SOUNDS)
sc = lambda n, g=None: {"narration": n, **({"graphic": g} if g else {})}
reel = [sc("Raat ko customer ka message aata hai"), sc("Aap ghar ja chuke ho aur staff nahi hai"), sc("Isliye customer kho dete ho", {"layout": "title", "heading": "Customer loss"}),
        sc("Ek chatbot yeh sab sambhal leta hai"), sc("Wo ek minute mein reply deta hai"), sc("Jawab tezi se milta hai"), sc("Comment karo DEMO")]
assert er.check(reel), "a reel with no effects fails the check"
notes = er.enforce(reel, seed="x")
assert not er.check(reel), notes
used = [er.effect_of(s) for s in reel]
assert len({u for u in used if u}) >= er.MIN_EFFECTS and used[0] is None and used[-1] is None, used      # the hook and the call to action are never touched
assert all(not (a and a == b) for a, b in zip(used, used[1:]))
assert sum(1 for s in reel if s.get("graphic")) <= int(len(reel) * er.MAX_GRAPHIC_SHARE) + 1
# every upgraded scene resolves to a real graphic with items (no empty effect)
words = [{"text": w, "start": 0.3 * i, "end": 0.3 * i + 0.25} for i, w in enumerate("ek chatbot yeh sab sambhal leta hai aur reply deta hai".split())]
for s in reel:
    if er.effect_of(s):
        p = graphics.resolve_graphic(s, words, 5.0)
        assert p and p["mock"]["type"] == er.effect_of(s) and p["mock"]["items"], s
# protected scenes stay as they are
r2 = [sc("a b c d"), sc("one two three", {"layout": "title", "heading": "Before after"}), sc("x y z w"), sc("p q r s"), sc("m n o p"), sc("last line here")]
er.enforce(r2, {1}, "y")
assert r2[1]["graphic"] == {"layout": "title", "heading": "Before after"}
# an already compliant reel is left alone
done = [sc("a")] + [sc(str(i), {"layout": "step", "heading": "x", "mock": {"type": t, "items": ["a"]}}) for i, t in enumerate(["giant", "bill", "tier", "wall"])] + [sc("z")]
assert not er.enforce(done, seed="z") and not er.check(done)
# captions: at least 3 different, never the same twice in a row, graphic scenes only get styles they can show
for look in ("pill", "hierarchy", "neon", "karaoke"):
    for g in ([False, True, False, True, False, True, False], [True, True, True, True], [False] * 5, [True, False, True]):
        caps = er.caption_plan(g, look, "t")
        assert len(set(caps)) >= min(er.MIN_CAPTIONS, len(g)) and all(a != b for a, b in zip(caps, caps[1:])), (look, g, caps)
        assert all((c in er.CLASSIC_CAPTIONS) for c, gg in zip(caps, g) if gg)
# sounds: all 16 are wired, each effect gets a cue that lands on its moment, over a few days every sound is used
assert sfxcustom.all_ids() == set(sfxcustom.load()) and len(sfxcustom.all_ids()) == 16
seen = set()
for day in range(10):
    for e in graphics.EFFECTS:
        b = {"graphic": {"mock": {"type": e}, "times": {"mock": 1.5, "items": [1.8]}}, "narration_seconds": 5.0, "sfx": []}
        c = sfxcustom.cues_for(b, day)
        assert len(c) == 1 and c[0]["file"] in sfxcustom.EFFECT_SOUNDS[e] and c[0]["atSecond"] >= 0 and (sfxcustom.DIR / f"{c[0]['file']}.wav").exists()
        seen.add(c[0]["file"])
assert seen == sfxcustom.all_ids(), sfxcustom.all_ids() - seen
print("ok")
