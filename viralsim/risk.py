"""Backlash/controversy detection (PhantomCrowd), negative-signal risk and discourse tension (Viralix)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .llm import LLMClient, extract_json

SEVERITY_PENALTY = {"low": 5, "medium": 12, "high": 25, "critical": 40}
RULES = [  # (category, regex, severity, note)
    ("gender stereotyping", r"\b(real (men|women)|like a girl|man up|women (can't|cannot|belong))\b", "high", "Stereotyped gender framing"),
    ("body shaming", r"\b(fat|lazy body|ugly|skinny shame|get in shape or)\b", "high", "Body-shaming language"),
    ("class discrimination", r"\bif you can't afford\b|\bpoor people\b", "high", "Economic shaming"),
    ("ageism", r"\b(boomer|too old to|okay boomer|over the hill)\b", "medium", "Age-based dismissal"),
    ("toxic positivity / shaming", r"\b(no excuses|stop being lazy|just be happy|you're just not trying)\b", "medium", "Shaming/toxic positivity"),
    ("exclusionary language", r"\bonly for\b|\bnot for (everyone|you)\b", "low", "Exclusionary framing"),
    ("ableism", r"\b(crazy|insane|psycho|retard\w*|lame)\b", "low", "Ableist slang"),
    ("tone-deaf", r"\b(pandemic|war|genocide|tragedy)\b.*\b(sale|discount|deal|giveaway|promo)\b", "critical", "Trivialises a serious issue"),
    ("religious insensitivity", r"\b(holy war|heathen|infidel)\b", "high", "Religious insensitivity"),
    ("slurs / hate", r"\b(n-word|faggot|tranny|chink|spic)\b", "critical", "Hate speech"),
]
ORDER = ["none", "low", "medium", "high", "critical"]


@dataclass
class RiskReport:
    overall_risk: str
    issues: list[dict]
    score_penalty: int
    source: str = "rules"

    @property
    def has_controversy(self) -> bool:
        return self.overall_risk != "none"


def detect_controversy(text: str, llm: LLMClient | None = None, market: str = "en") -> RiskReport:
    issues = []
    for cat, pat, sev, note in RULES:
        if re.search(pat, text, re.I):
            issues.append({"category": cat, "severity": sev, "description": note, "score_penalty": SEVERITY_PENALTY[sev]})
    source = "rules"
    if llm is not None:
        prompt = (f"Audit this marketing/social content for backlash risk in market '{market}'. Check gender, race, age, body, class, "
                  "culture, religion, disability, LGBTQ+, tone-deafness, exclusion, toxic positivity. Do not excuse stereotypes.\n"
                  f"Content: '''{text}'''\nReturn JSON: {{\"issues\":[{{\"category\":str,\"severity\":\"low|medium|high|critical\","
                  "\"description\":str}}]}")
        try:
            for it in extract_json(llm.complete("You are a cultural sensitivity analyst.", prompt, json_mode=True)).get("issues", []):
                sev = it.get("severity", "low")
                if sev in SEVERITY_PENALTY and not any(i["category"] == it.get("category") for i in issues):
                    issues.append({"category": it.get("category", "other"), "severity": sev,
                                   "description": it.get("description", ""), "score_penalty": SEVERITY_PENALTY[sev]})
            source = "rules+llm"
        except Exception:      # LLM unavailable/invalid -> rules only, never crash the pipeline
            pass
    worst = max((ORDER.index(i["severity"]) for i in issues), default=0)
    return RiskReport(ORDER[worst], issues, min(40, sum(i["score_penalty"] for i in issues)), source)


POS = set("love great amazing awesome good brilliant excellent happy win agree thanks perfect best wow".split())
NEG = set("hate awful terrible bad worst cringe disgusting angry trash scam lies wrong boring sad fail".split())


def lexicon_sentiment(text: str) -> str:
    w = re.findall(r"[a-z']+", text.lower())
    p, n = sum(x in POS for x in w), sum(x in NEG for x in w)
    if p and n:
        return "controversial"
    return "positive" if p > n else "negative" if n > p else "neutral"


def discourse_tension(actions: list[dict], llm: LLMClient | None = None, max_samples: int = 30) -> dict:
    """Fraction of comments whose declared sentiment disagrees with sentiment read from the text.
    High tension = agents say one thing and write another (a sign of sarcasm or an unreliable simulation)."""
    comments = [a for a in actions if a.get("content") and a.get("action") in ("reply", "post", "comment")][-max_samples:]
    if not comments:
        return {"discourse_tension_score": 0.0, "judged": 0, "disagreements": 0}
    norm = {"mixed": "controversial", "sarcastic": "negative"}
    dis = 0
    for a in comments:
        declared = norm.get(a.get("sentiment", "neutral"), a.get("sentiment", "neutral"))
        dis += declared != lexicon_sentiment(a["content"])
    return {"discourse_tension_score": round(dis / len(comments), 4), "judged": len(comments), "disagreements": dis}
