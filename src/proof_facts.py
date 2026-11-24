"""What the scriptwriter may say about the real proof screenshots (video-agent/assets/proof/index.json).

A script may tell the viewer only what a screenshot shows: "I messaged a <type>, delivered on <date>, no reply by <date>" or "a business's own WhatsApp AI answered within a minute".
Never a count of businesses, a percentage, "all businesses", a name, or that the chatbot is ours / brings customers. Stale or missing proofs are not offered, and a script that
claims a test without one is rejected."""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

INDEX = Path(__file__).resolve().parent.parent / "video-agent" / "assets" / "proof" / "index.json"
MAX_AGE_DAYS = 45                       # same window as video-agent/agent/proof.py


def _fresh(today: date | None = None) -> list[dict]:
    today = today or date.today()
    try:
        rows = json.loads(INDEX.read_text()).get("proofs", [])
    except (OSError, ValueError):
        return []
    out = []
    for p in rows:
        try:
            age = (today - datetime.strptime(p["checked"], "%Y-%m-%d").date()).days
        except (KeyError, ValueError):
            continue
        if 0 <= age <= MAX_AGE_DAYS and (INDEX.parent / str(p.get("file", ""))).exists() and ("no reply" in str(p.get("status", "")) or p.get("kind") == "ai_reply"):
            out.append(p)
    return out


def _d(s: str) -> str:
    return datetime.strptime(s, "%Y-%m-%d").strftime("%-d %b")


def facts(today: date | None = None) -> list[dict]:
    """Fact-sheet rows (ids p1, p2..) for the fresh proofs, so the script may cite them and the meaning check sees them."""
    out = []
    for i, p in enumerate(_fresh(today), 1):
        if p.get("kind") == "ai_reply":
            claim = "Ek business ka apna WhatsApp AI assistant, ek mystery customer ke 'Hi' ka reply ek minute ke andar de deta hai."
        else:
            claim = f"Maine ek local {p['business_type']} ko WhatsApp par message kiya ({_d(p['sent'])}). Message deliver hua, lekin {_d(p['checked'])} tak koi reply nahi aaya."
        out.append({"id": f"p{i}", "claim": claim, "source": f"AR Designs ka apna mystery-customer test, {_d(p['checked'])} ko dobara dekha", "proof": p["id"]})
    return out


def block(today: date | None = None) -> str:
    rows = facts(today)
    if not rows:
        return ""
    lines = "\n".join(f"  {r['id']}: {r['claim']}" for r in rows)
    return ("REAL PROOF (optional; the video shows a real, blurred screenshot of each). You may use AT MOST ONE no-reply proof and the AI-reply proof, in the poke or the payoff, "
            "cite its id in `facts`, and say it only as written, in your own Hinglish words:\n" + lines +
            "\nNEVER: say how many businesses were tested, a percentage, 'sab / har / zyadatar businesses', a name or place, that the AI reply is ours, or that it brings customers or sales. "
            "One proof is one example, not a trend. Without a proof listed here, never claim you tested or messaged a business.\n")


TEST_CLAIM = re.compile(r"\b(maine|humne|hamne|mene)\b.{0,60}\b(message|msg|whatsapp|text)\b.{0,70}\b(reply|jawab|jawaab)\b", re.I)
OVER_CLAIM = re.compile(r"(?:\b(?:sab|saare|saari|har|zyadatar|kaafi|bahut se)\b|\d+\s*(?:%|percent\b|prati?shat\b)|\d+\s*(?:me se|mein se|out of)\b).{0,30}\b(business|businesses|dukaan|shop|clinic|gym|hotel|cafe|restaurant)s?\b.{0,40}\b(reply|jawab|jawaab|answer)\b", re.I)
FAKE_OWN = re.compile(r"\b(hamara|humara|hamare|humare|our)\b.{0,25}\b(chatbot|bot|ai)\b.{0,40}\b(reply|jawab)\b", re.I)


def problems(lines: list[str], today: date | None = None) -> list[str]:
    """Hard accuracy checks on the spoken lines (empty when the script says nothing about proofs)."""
    have = facts(today)
    out = []
    for ln in lines:
        ln = str(ln or "")
        if OVER_CLAIM.search(ln):
            out.append("proof: generalises from a few tests ('sab / har / % businesses'); one screenshot is one example, say 'maine ek <type> ko message kiya' only")
        if TEST_CLAIM.search(ln) and not have:
            out.append("proof: claims a test of a business's WhatsApp reply but no fresh proof exists; remove the claim")
        if FAKE_OWN.search(ln):
            out.append("proof: presents the business's own AI reply as our product; say 'ek business ka apna AI assistant' instead")
    return out
