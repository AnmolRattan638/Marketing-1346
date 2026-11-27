"""LinkedIn is a person talking, not an ad: rotation (a pitch only one post in five, at most 30%), the gate (no DM/price/pay-after-approval, no banned facts, no number outside the facts file,
a curious hook), the writer's retry with concrete lessons, no post at all when nothing passes, and publishing skips an empty post."""
import json, pathlib, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import config, linkedin_story as ls, scriptlessons as SL
from src.agents import linkedin_writer as lw

fx = ls.facts()
SL.STATE = pathlib.Path(tempfile.mkdtemp()) / "lessons.json"
GOOD = ("My content system once read “24x7” as “24 times 7.”\n\n"
        "It is a program that writes short videos, reads them out in an AI voice and posts them every day. I only noticed because the voiceover sounded strange. The script was fine, but the voice said the symbol the way it was written.\n\n"
        "So I went looking and found more. A price ran into the next word. “4K” became “4 thousand”. A slash turned a short phrase into nonsense.\n\n"
        "I built a pronunciation list from those mistakes, and now every script is checked for words the voice would say wrong before anything is recorded.\n\n"
        "It is a small fix, but it taught me something: a system that talks has to be checked by listening, not only by reading.\n\n"
        "If you build things too, I would like to connect and hear what you got wrong first.")
assert ls.MIN_WORDS <= len(GOOD.split()) <= ls.MAX_WORDS, len(GOOD.split())
assert ls.problems(GOOD, "story", fx) == [], ls.problems(GOOD, "story", fx)

# 1. rotation: intro first, a pitch exactly one post in five, every topic used before one repeats
h, seq = [], []
for _ in range(15):
    m, t = ls.choose(fx, h); seq.append(m); h.append({"mode": m, "topic": t})
assert seq[0] == "intro" and seq.count("pitch") == 3 and [i for i, m in enumerate(seq) if m == "pitch"] == [4, 9, 14], seq
assert "pitch" not in seq[:4] and all(seq[i] != "pitch" or seq[i - 1] != "pitch" for i in range(1, 15))
pool = {t["id"] for t in fx["topics"] if t["mode"] == "story"}
seen_t = set()
for x in h:                                                  # a story topic (told on a story day or under a pitch) repeats only after ALL of them were used
    if x["topic"] in pool:
        if x["topic"] in seen_t:
            assert seen_t == pool, (x["topic"], seen_t)
            break
        seen_t.add(x["topic"])
assert seen_t == pool or len(h) < 13
# 2. the gate: each of your rules, with a concrete reason
def tags(text, mode="story", pitch=()): return sorted({p.split("]")[0].split("[")[1] for p in ls.problems(text, mode, fx, pitch)})
assert "pitchy" in tags(GOOD + "\n\nDM SITE and pay after approval.") and "pitchy" in tags(GOOD.replace("connect", "connect, prices start at ₹999"))
assert "pitchy" in tags(GOOD + "\n\nHire me for your website.") and "pitchy" not in tags(GOOD + "\n\nHire me for your website.", "pitch", ["Hire me for your website."]), "a sell phrase is only allowed on a pitch day"
assert "never" in tags(GOOD.replace("My content system", "Ratty, my chatbot")) and "never" in tags(GOOD.replace("a system", "a student project"))
assert "never" in tags(GOOD.replace("build things", "build things since 3 years"))
assert "numbers" in tags(GOOD.replace("every script", "every one of 500 scripts")) and "numbers" in tags(GOOD + "\n\nI have 5 clients.")
assert ls.problems(GOOD.replace("24x7", "24x7"), "story", fx) == [], "numbers that are in the facts file (24, 7, 4) are fine"
assert "hook" in tags(GOOD.replace(GOOD.splitlines()[0], "Small businesses waste hours on this every week.")) and "hook" in tags(GOOD.replace(GOOD.splitlines()[0], "THIS CHANGES EVERYTHING!"))
assert "hook" in tags(GOOD.replace(GOOD.splitlines()[0], "word " * 30)), "a hook over 22 words"
assert "links" in tags(GOOD + "\n\nSee anmolrattan.netlify.app") and "shape" in tags(GOOD + " #buildinpublic") and "length" in tags("Too short.\n\nReally.\n\nYes.")
assert "shape" in tags(GOOD, "question"), "a question post must end with its question"
assert tags(GOOD.rstrip(" .") + "?\n", "question") == [], "...and passes when it does"
assert "shape" in tags(GOOD.replace("Anmol", "x"), "intro")
reason = ls.problems(GOOD.replace("My content system", "Ratty"), "story", fx)[0]
assert "\"Ratty\"" in reason and reason.startswith("linkedin[never]:"), reason
for line in ("The client pays only after approving the work.", "Payment happens only after you approve the final clip.", "You pay after you approve it.", "Pay once approved."):
    assert "pitchy" in tags(GOOD.replace("connect", "connect. " + line)), line          # the phrases from the post that slipped through before
assert tags(GOOD.replace("connect", "connect. I paid for the domain after testing it")) == [], "ordinary words are not flagged"
# 2b. context: the post that got 136 impressions named "my content system" and never said what it is
REAL = ("My content system once read “24x7” as “24 x 7.”\n\nIt sounded wrong. I kept listening to the recordings.\n\nSome amounts ran into the next word. “4K” became “4 thousand.” “show/hide” turned into nonsense and I noted them all.\n\n"
        "I built a pronunciation list. Now every script is checked for words the voice would say wrong before it is recorded. I do not skip this step, every time.\n\nI used to record first and fix later. Now I check first. It takes longer and sounds right every time.\n\n"
        "The voice does not forgive small mistakes. I am still working it out. If you build things, I would be glad to connect.")
assert "context" in tags(REAL), tags(REAL)
assert [p for p in ls.problems(REAL, "story", fx) if "[context]" in p][0].count("content system") == 1 and "writes short videos" in ls.problems(REAL, "story", fx)[0] + " ".join(ls.problems(REAL, "story", fx))
assert "context" not in tags(GOOD), "explained in the second paragraph: fine"
assert "context" in tags(GOOD.replace("It is a program that writes short videos, reads them out in an AI voice and posts them every day. ", "")), "remove the explanation and it fails"
assert "context" in tags(GOOD.replace("My content system", "Our Lead Finder").replace("It is a program that writes short videos, reads them out in an AI voice and posts them every day. ", "")), "every named thing needs its explanation"
assert "context" not in tags(GOOD.replace("My content system", "My small program").replace("It is a program that writes short videos, reads them out in an AI voice and posts them every day. ", "")), "no named thing, nothing to explain"
for tid in ("24x7", "rejects-itself", "tool-to-platform"):
    assert any("automated content system" in f or "Lead Finder is a tool" in f for f in ls.topic_facts(fx, tid)["facts"][:1]), tid     # those stories start by saying what the thing is
assert "CONTEXT FIRST" in lw.prompt(fx, "story", "24x7") and "writes short videos" in lw.prompt(fx, "story", "24x7")
# 3. a pitch day: the offer is declared word for word and is at most 30% of the post
offer = "I build websites for small businesses and I am open to freelance projects."
pitch_post = GOOD + "\n\n" + offer
assert tags(pitch_post, "pitch", [offer]) == [] or tags(pitch_post, "pitch", [offer]) == ["length"], tags(pitch_post, "pitch", [offer])
assert "pitch-share" in tags(pitch_post, "pitch"), "an undeclared offer"
assert "pitch-share" in tags(pitch_post, "pitch", ["I never wrote this sentence."])
long_offer = " ".join([offer] * 14)
assert "pitch-share" in tags(GOOD + "\n\n" + long_offer, "pitch", [long_offer]) or "length" in tags(GOOD + "\n\n" + long_offer, "pitch", [long_offer])
assert "pitch-share" in tags(GOOD, "story", [offer]), "no offer on a normal day"
assert "pitch-share" in tags(GOOD + "\n\nI can help you with a website, message me.", "pitch", [offer]), "a hidden offer outside the declared sentences"

# 4. the writer: a rejected draft is recorded as a concrete lesson, shown to the next attempt, and the post that finally passes is used
seen = []
def ask(prompt, system):
    seen.append(prompt)
    return {"post": GOOD.replace("My content system", "Ratty, my chatbot")} if len(seen) == 1 else {"post": GOOD}
res = lw.run("story", "24x7", fx, ask=ask)
assert res["post"] == GOOD and res["attempts"] == 2 and res["problems"] == []
assert "YOUR LAST DRAFT WAS REJECTED" in seen[1] and "\"Ratty\"" in seen[1], "the next attempt is told exactly what failed"
lessons = SL.load()
assert lessons["linkedin-never"]["count"] == 1 and "Ratty" in lessons["linkedin-never"]["recent"][-1]["mistake"], lessons
nxt = lw.prompt(fx, "story", "24x7")
assert "LAST TIME you wrote this and it was rejected" in nxt and "Ratty" in nxt and "A LinkedIn post is a person talking" in nxt, "the lesson reaches the next day's prompt"
assert "no ALL-CAPS word except the DM keyword" not in nxt, "reel lessons stay out of the LinkedIn prompt"
assert "linkedin-never" not in SL.prompt_block() and "Ratty" not in SL.prompt_block(), "and LinkedIn lessons stay out of the reel prompt"
# prompt content: facts only, hook guidance, no Instagram pitch
p = lw.prompt(fx, "intro", "who-i-am")
assert "ABOUT ANMOL" in p and "Himachal Pradesh" in p and "Old British House" not in p and "HOOK" in p and "BANNED: DM, prices" in p
assert "OFFER" not in p and "OFFER (the only thing you may offer" in lw.prompt(fx, "pitch", "tool-to-platform")
# 5. nothing passes -> no post (and a lesson for each attempt), never a bad post
SL.STATE = pathlib.Path(tempfile.mkdtemp()) / "lessons2.json"
none = lw.run("story", "24x7", fx, ask=lambda p, s: {"post": "Small businesses need DM SITE now!"}, tries=3)
assert none["post"] == "" and none["attempts"] == 3 and none["problems"], none
assert SL.load()["linkedin-pitchy"]["count"] >= 1 and SL.load()["linkedin-hook"]["count"] >= 1
# 5b. an empty or missing reply is an outage, not a writing mistake: retried, never recorded as a lesson
SL.STATE = pathlib.Path(tempfile.mkdtemp()) / "lessons3.json"
calls = []
out = lw.run("story", "24x7", fx, ask=lambda p, s: calls.append(1) or {}, tries=3)
assert out["post"] == "" and len(calls) == 3 and SL.load() == {}, (out, SL.load())
# 6. the facts file is complete and safe
assert all(t["mode"] in ("story", "build", "question", "intro") for t in fx["topics"]) and len({t["id"] for t in fx["topics"]}) == len(fx["topics"])
assert {t["mode"] for t in fx["topics"]} == {"story", "build", "question", "intro"}
for t in fx["topics"]:
    assert ls.topic_facts(fx, t["id"])
assert "Old British House" in fx["never_say"]["phrases"] and "oldbritishhouse" not in json.dumps({k: v for k, v in fx.items() if k != "never_say"}).lower()
assert fx["rules"]["pitch_max_share"] == 0.3 and fx["rules"]["pitch_one_post_in"] == 5

# 7. publishing skips an empty LinkedIn post and the humanizer never touches LinkedIn
from src import humanize
assert humanize.humanize_posts.__defaults__ == (("linkedin",),)
src = (config.ROOT / "src" / "publish.py").read_text(encoding="utf-8")
assert 'no post today, nothing was posted' in src
print("linkedin story test passed: one pitch in five, 30% cap, gate rules, concrete lessons, no post when nothing passes")
