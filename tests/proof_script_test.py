"""Offline test: the scriptwriter may use the real proofs only as written, and never over-claims from them."""
import pathlib, sys
from datetime import date
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from src import proof_facts as pf
from src.agents import scriptwriter as sw

today = date(2026, 11, 24)
rows = pf.facts(today)
ids = {r["id"] for r in rows}
assert len(rows) == 6 and ids == {"p0", "p1", "p2", "p3", "p4", "p5"}, ids
sample = next(r for r in rows if r["id"] == "p0")
assert sample["n"] == 5 and sample["k"] == 4 and "5 local businesses" in sample["claim"] and "4 ne 23 Nov tak reply nahi kiya" in sample["claim"], sample["claim"]
joined = " ".join(r["claim"] for r in rows)
assert "gym" in joined and "restaurant" in joined and "ek minute" in joined
assert not any(w in joined.lower() for w in ("pirates", "zoca", "kake", "aayojan", "aesthetic", "bhubaneswar", "+91")), "no names in what the writer sees"
assert all("sab " not in r["claim"].lower().replace("sab businesses ka", "") and "%" not in r["claim"] for r in rows)
blk = pf.block(today)
assert "REQUIRED" in blk and "NEVER" in blk and "p1:" in blk

# every reel must cite exactly one proof (p1..) in the poke or payoff beat while a fresh proof exists
assert pf.required([{"beat": "poke", "facts": ["f1"]}], today), "no proof cited"
assert not pf.required([{"beat": "poke", "facts": ["p1"]}, {"beat": "fix", "facts": []}], today)
assert not pf.required([{"beat": "payoff", "facts": ["p5"]}], today)
assert pf.required([{"beat": "poke", "facts": ["p1"]}, {"beat": "payoff", "facts": ["p2"]}], today), "two proofs"
assert pf.required([{"beat": "pain", "facts": ["p1"]}], today), "wrong beat"
assert pf.required([{"beat": "poke", "facts": ["p0"]}], today), "p0 is a sample count, it has no screenshot"
assert pf.required([{"beat": "poke", "facts": []}], date(2027, 6, 1)) == [], "stale proofs: nothing to require"

# stale proofs are not offered, and then a test claim is rejected
late = date(2027, 6, 1)
assert pf.facts(late) == [] and pf.block(late) == ""
assert pf.problems(["Maine 5 businesses ko message kiya, 4 ne reply nahi kiya."], late), "the sample claim needs fresh proofs too"
assert pf.problems(["Maine ek gym ko WhatsApp message kiya, par koi reply nahi aaya."], late), "claim with no fresh proof"
assert not pf.problems(["Maine ek gym ko WhatsApp message kiya, par koi reply nahi aaya."], today), "fine with a fresh proof"

# over-claims are always rejected
for bad in ("Maine kai gym ko message kiya aur sab business ne reply nahi diya.", "Zyadatar business WhatsApp par reply nahi karte.", "Maine test kiya aur 80% business ne reply nahi kiya.", "Maine 5 business ko test kiya, 80 percent ne reply nahi kiya.", "Ye hamara chatbot ek minute mein reply deta hai."):
    assert pf.problems([bad], today), bad
for ok in ("Maine 5 businesses ko WhatsApp par message kiya, aur 4 ne reply nahi kiya.", "Jin businesses ko maine message kiya, unmein se zyadatar ne reply nahi kiya.", "Raat 9 baje customer ka message aaya aur staff ghar ja chuka hai.", "Maine ek restaurant ko message kiya, delivered hua, lekin reply nahi aaya.", "Ek business ka apna AI assistant ek minute mein reply de deta hai."):
    assert not pf.problems([ok], today), ok

# wiring: the prompt carries the block, problems() runs the check, finish() turns a cited proof into a marker and keeps it off the real fact list
src = (pathlib.Path(sw.__file__)).read_text()
assert "proof_facts.block()" in src and "proof_facts.problems(" in src and "real_facts" in src
script = {"beats": [{"beat": "poke", "line": "x", "facts": ["f1", "p1"]}]}
sw.finish(script, {"facts": [{"id": "f1", "claim": "a"}]}, {"id": "bot"})
b = script["beats"][0]
assert b["facts"] == ["f1"] and b["proof"] and b["proof"][0] in {p["id"] for p in __import__("json").loads(pf.INDEX.read_text())["proofs"]}
mg = (pathlib.Path(__file__).resolve().parent.parent / "video-agent/agent/master_script.py").read_text()
assert "REAL PROOF: use graphic mock type proof" in mg
print("proof script ok")
