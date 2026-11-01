"""Content understanding: text -> 8 engagement dimensions (0-10), topics, entities.

Two scorers behind one interface:
  * HeuristicScorer  - offline, deterministic, coarse (lexical cues). Good for drafts and tests.
  * LLMScorer        - anchored-rubric prompt (Content-diffusion) via any LLMClient; validated JSON.
"""
from __future__ import annotations

import re

from .llm import LLMClient, extract_json
from .schema import DIMS, TOPICS, Content, clamp
from .signals import analyze_text

RUBRIC = """humor 0=none 4=mildly amusing 7=clearly funny to most 10=laugh-out-loud
curiosity 0=nothing intriguing 4=mild interest 7=real open loop 10=irresistible need-to-know
educational 0=teaches nothing 4=minor takeaway 7=clear useful lesson 10=densely valuable
novelty 0=generic 4=fresh angle 7=distinctly original 10=nothing else like it
controversy 0=universally agreeable 4=mild disagreement 7=opposing camps 10=highly polarizing (a signal, not 'good')
emotional_intensity 0=flat 4=noticeable 7=strong 10=intense high-arousal (judge arousal, not valence)
relatability 0=niche 4=subgroup 7='that's so me' for many 10=near-universal
practical_value 0=nothing actionable 4=a tip 7=how-to worth keeping 10=immediately actionable"""

TOPIC_WORDS = {
    "comedy": "funny joke lol meme hilarious prank", "gaming": "game gaming gamer xbox playstation steam esports",
    "tech": "ai software app code startup gadget tech", "fitness": "workout gym fitness lifting cardio",
    "food_cooking": "recipe cooking food dinner bake chef", "beauty_fashion": "makeup skincare fashion outfit style",
    "travel": "travel trip flight hotel vacation", "music": "song album music concert band",
    "sports": "football soccer nba nfl match goal team", "education_howto": "learn tutorial how-to guide lesson tips",
    "news_politics": "election government politics policy senate", "finance_business": "money invest stock business revenue startup",
    "art_design": "art design illustration drawing", "science": "science research study physics space",
    "lifestyle_vlog": "vlog routine day-in-my-life lifestyle", "parenting_family": "kids parenting family baby",
    "pets_animals": "dog cat puppy pet animal", "automotive": "car engine tesla driving",
    "diy_crafts": "diy craft handmade build", "motivation_selfhelp": "motivation mindset habits discipline success",
    "relationships": "dating relationship marriage love partner", "nature_outdoors": "hiking nature outdoors camping",
    "film_tv": "movie film series trailer netflix", "health_wellness": "health sleep wellness therapy nutrition"}


class HeuristicScorer:
    def score(self, text: str, **media) -> Content:
        f = analyze_text(text, **media)
        t = text.lower()
        words = re.findall(r"[a-z']+", t)
        n = max(1, len(words))
        hits = lambda pat: len(re.findall(pat, t))
        excl = text.count("!")
        caps = sum(1 for w in re.findall(r"\b[A-Z]{3,}\b", text))
        d = dict.fromkeys(DIMS, 0.0)
        d["humor"] = 2 + 2 * hits(r"\b(lol|lmao|haha|funny|joke|meme)\b") + 1.5 * f.emojis * (1 if re.search("😂|🤣|💀", text) else 0.3)
        d["curiosity"] = 2 + 2.5 * f.has_question + 2.5 * f.has_hook + 1.5 * bool(re.search(r"\d", t)) + 1.5 * bool(re.search(r"\.\.\.|…|secret|nobody|truth", t))
        d["educational"] = 1 + 2 * hits(r"\b(because|learn|how to|why|study|research|explained|tip)\b") + 1.5 * bool(re.search(r"\d+\s*(ways|tips|steps|lessons|things)", t))
        d["novelty"] = 3 + 4 * (len(set(words)) / n - 0.7) + 2 * f.absurd
        d["controversy"] = 1 + 4 * f.controversial + 1.5 * hits(r"\b(wrong|overrated|unpopular|never|worst|stop)\b")
        d["emotional_intensity"] = 2 + 1.2 * excl + 0.8 * caps + 1.5 * hits(r"\b(love|hate|angry|amazing|heartbreaking|incredible|terrified|furious)\b") + 0.4 * f.emojis
        d["relatability"] = 2 + 3 * min(1.0, hits(r"\b(you|we|my|me|our|us|i)\b") / (0.15 * n + 1)) + 1.5 * hits(r"\b(everyone|always|ever|same)\b")
        d["practical_value"] = 1 + 2.5 * hits(r"\b(how to|step|tip|use|try|template|checklist|guide)\b") + 1.5 * bool(re.search(r"^\s*\d+[.)]", text, re.M))
        dims = {k: round(clamp(v, 0, 10), 1) for k, v in d.items()}
        topics = {}
        for tp, words_ in TOPIC_WORDS.items():
            if any(re.search(rf"\b{re.escape(w)}\b", t) for w in words_.split()):
                topics[tp] = 1.0
        ents = list(dict.fromkeys(re.findall(r"\b(?:[A-Z][a-z]+(?:\s[A-Z][a-z]+)+)\b", text)))
        tags = re.findall(r"#\w+", text)
        return Content(text=text, dims=dims, topics=dict(list(topics.items())[:3]), entities=ents, tags=tags,
                       has_video=f.has_video, has_image=f.has_image, is_thread=f.is_thread,
                       thread_length=f.thread_length).ensure_composites()


class LLMScorer:
    SYSTEM = ("You are a calibrated content-analysis engine. Score how a broad general audience would react, not "
              "personal taste. Ground each score in evidence; if signal is absent, score low. Identical content gets identical scores.")

    def __init__(self, llm: LLMClient, fallback: HeuristicScorer | None = None):
        self.llm, self.fallback = llm, fallback or HeuristicScorer()

    def score(self, text: str, **media) -> Content:
        prompt = (f"Content:\n'''{text}'''\n\nRubric (0-10 anchors):\n{RUBRIC}\n\nTopics (pick 1-3): {', '.join(TOPICS)}\n"
                  'Return JSON only: {"dims": {<each of ' + ", ".join(DIMS) + '>: number}, "topics": [..], "entities": [..]}')
        try:
            data = extract_json(self.llm.complete(self.SYSTEM, prompt, json_mode=True, temperature=0.0))
            dims = {k: clamp(float(data["dims"][k]), 0, 10) for k in DIMS}
        except (ValueError, KeyError, TypeError):
            return self.fallback.score(text, **media)
        f = analyze_text(text, **media)
        return Content(text=text, dims=dims, topics={t: 1.0 for t in data.get("topics", []) if t in TOPICS},
                       entities=[e for e in data.get("entities", []) if isinstance(e, str)],
                       tags=re.findall(r"#\w+", text), has_video=f.has_video, has_image=f.has_image,
                       is_thread=f.is_thread, thread_length=f.thread_length).ensure_composites()
