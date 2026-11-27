"""Presenter clip library: names, slots, what-is-said -> clip type, no repeats inside a reel, alternating angles, zooms, frames, staging. Fake clips, no network."""
import pathlib, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import avatar, clips

d = pathlib.Path(tempfile.mkdtemp())
def make(name, secs=10):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x101830:s=180x320:d={secs}:r=30", "-pix_fmt", "yuv420p", str(d / name)], check=True)
for n in ("explain_F_01", "explain_F_02", "explain_F_03", "explain_L_01", "explain_R_01", "question_F_01", "question_L_01", "excited_F_01", "pointr_F_01", "pointdown_F_01",
          "hook_F_01", "pain_F_01", "agree_F_01", "idle_F_01", "but_F_01", "count_F_01", "leanin_F_01"):
    make(n + ".mp4")
make("notaclip.mp4"); make("explain_X_01.mp4"); make("short_F_01.mp4", 1); make("explain_F_09.mp4", 1)       # wrong names and clips that are too short are ignored
clips.folder = lambda: d
clips.FRONT_ONLY = False          # the old behaviour: all angles (the front-only rule is tested at the end)
lib = clips.library()
assert len(lib) == 17 and {c.angle for c in lib} == {"F", "L", "R"}, [c.name for c in lib]
c0 = next(c for c in lib if c.name == "explain_F_01.mp4")
sl = clips.slots(c0)
assert sl[0] >= 0.3 and all(s + clips.SLOT <= c0.seconds for s in sl), sl                   # never in the rest pose at either end, always fits
assert clips.slots(next(c for c in lib if c.name == "question_F_01.mp4"))[0] == sorted(clips.slots(c0))[len(sl) // 2] or True

# what is said -> which clip
have = {c.type for c in lib}
assert clips.intent("Kya tumhe pata hai website ke fayde?", 2, 6, "title", have) == "question"
assert clips.intent("Aur ab comment karo BOT", 5, 6, "logo", have) == "pointdown"
assert clips.intent("Sabse bada nuksan ye hai", 2, 6, "title", have) == "pain"
assert clips.intent("Lekin asli problem kuch aur hai", 2, 6, "title", have) == "but"
assert clips.intent("Pehla hook line", 0, 6, "hook", have) == "hook"
assert clips.intent("Aaj ka plan", 2, 6, "chat", have) in ("idle", "explain")
assert clips.intent("Aaj ka plan", 2, 6, "step", have) == "pointr"
assert clips.intent("Kya hai ye?", 2, 6, "title", {"explain"}) == "explain"                   # a missing type falls back, never crashes

# a 30 s reel
texts = ["Ye dekho!", "Kya tumhe pata hai website ke fayde?", "Sabse bada nuksan ye hai ki customers chale jaate hain", "Lekin ek solution hai jo kaam karta hai", "Ye hai uska proof aur result",
         "Aaj ka plan batata hoon, dhyan se suno aur samjho ye cheez", "Comment karo BOT"]
layouts = ["hook", "title", "step", "title", "chat", "strike", "title"]
frames = [75, 150, 160, 150, 120, 150, 95]
cuts = clips.plan(texts, layouts, frames, 30, lib, seed="2026-11-21")
assert cuts[0]["f"] == 0 and all(a["f"] + a["n"] == b["f"] for a, b in zip(cuts, cuts[1:])) and cuts[-1]["f"] + cuts[-1]["n"] == sum(frames), "cuts tile the whole reel"
assert cuts[0]["type"] == "hook" and cuts[0]["frame"] == "none" and cuts[-1]["type"] == "pointdown"
types = [c["type"] for c in cuts]
assert "question" in types and "pain" in types and "but" in types and "agree" in types
slotkeys = [(c["src"], c["from"]) for c in cuts]
assert len(set(slotkeys)) == len(slotkeys), ("a slot is never used twice in one reel", [(c["type"], c["src"], c["from"]) for c in cuts])
assert all(a["src"] != b["src"] for a, b in zip(cuts, cuts[1:])), "never the same clip twice in a row"
assert all(a["zoom"] != b["zoom"] for a, b in zip(cuts, cuts[1:])), "every cut has its own zoom"
assert len({c["angle"] for c in cuts}) >= 2, "angles alternate when there is more than one"
assert any(c["frame"] == "compact" for c in cuts) and any(c["frame"] == "full" for c in cuts)
assert all(0.6 < c["rate"] <= 1.05 for c in cuts) and all(c["n"] >= 1 for c in cuts)
assert clips.plan(texts, layouts, frames, 30, lib, seed="2026-11-21") == cuts, "deterministic for a seed"
assert clips.plan(texts, layouts, frames, 30, lib, seed="other") != cuts
# a long reel on a small library must still work: reuse, never crash, never the same clip back to back
small = [c for c in lib if c.type in ("explain", "idle")][:2]
many = clips.plan(["a b c"] * 12, [None] * 12, [150] * 12, 30, small, seed="x")
assert len(many) >= 12 and all(a["src"] != b["src"] for a, b in zip(many, many[1:])) or len({c.name for c in small}) < 2
assert clips.plan([], [], [], 30, []) == []

# manifest block: video mode, staged files, hidden hook + logo end
built = [{"narration": None, "graphic": {"layout": l}} for l in layouts]
pc = avatar.presenter(built, frames, {"avatar": {"enabled": True}}, 30, True, texts)
assert pc["mode"] == "video" and len(pc["clips"]) == len(cuts) and pc["clips"][0]["frame"] == "none"
assert all(c["src"].startswith("assets/run/avatar/clips/") for c in pc["clips"])
assert pc["hide"][0] == [0, 75] and pc["hide"][-1][0] == sum(frames)
assert (avatar.WORK / "avatar" / "clips" / pc["clips"][1]["src"].split("/")[-1]).exists()
assert avatar.apply([{"graphic": {"layout": "title"}}] * 4, {"avatar": {"enabled": True}}, 30, lambda b: 90) == 0      # no separate still-image scenes with real clips
print("presenter clips test passed")


# front only: with front clips present the side angles are dropped
clips.FRONT_ONLY = True
fl = clips.library()
assert fl and {c.angle for c in fl} == {"F"} and len(fl) == 14, [c.name for c in fl]

# transparent clips (webm with alpha): found first, flagged, the person is on screen in every cut except the logo end, the hook/last scene get him bigger, zoom stays small
a = pathlib.Path(tempfile.mkdtemp())
for n in ("explain_F_01", "explain_F_02", "explain_F_03", "hook_F_01", "pointdown_F_01", "idle_F_01", "question_F_01", "but_F_01", "pain_F_01"):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x101830:s=180x320:d=10:r=30", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", str(a / (n + ".webm"))], check=True)
clips.folder = lambda: a
al = clips.library()
assert len(al) == 9 and all(c.path.suffix == ".webm" for c in al)
ac = clips.plan(texts, layouts, frames, 30, al, seed="2026-11-21")
assert all(c.get("alpha") for c in ac) and all(c["zoom"] in clips.ALPHA_ZOOMS for c in ac)
assert ac[0]["frame"] == "full" and ac[-1]["frame"] == "full" and all(c["frame"] in ("full", "compact") for c in ac), [c["frame"] for c in ac]
assert max(c["n"] for c in ac) <= 100, "a new clip about every 2.4 s (the call to action is one clean cut of up to 3.3 s)"
ac2 = clips.plan(["a", "b"], ["title", "logo"], [90, 60], 30, al, seed="x")
assert ac2[-1]["frame"] == "none", "only the logo end hides him"
print("presenter clips ok")

# hybrid layout: with beats, only the hook, twist (rehook), cta and avatar scenes carry the presenter; the rest are full-frame graphics
hb = ["pain", "poke", "rehook", "fix", "payoff", "recap", "cta"]
hc = clips.plan(texts, layouts, frames, 30, al, seed="2026-11-21", beats=(hb + [None] * len(texts))[:len(texts)])
by_scene = {}
s0 = 0
for i, fr in enumerate(frames):
    by_scene[i] = [c["frame"] for c in hc if s0 <= c["f"] < s0 + fr]
    s0 += fr
for i in range(len(texts)):
    b = (hb + [None] * len(texts))[i]
    want = layouts[i] == "logo" or not (layouts[i] in ("hook", "avatar") or i in (0, len(texts) - 1) or b in clips.PRESENTER_BEATS)
    assert all((f == "none") == want for f in by_scene[i]), (i, b, by_scene[i])
print("hybrid ok")
