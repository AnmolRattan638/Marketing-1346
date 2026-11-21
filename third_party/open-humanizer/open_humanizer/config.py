"""
Open-Humanizer configuration: adversarial agent system prompts and detection rules.

Research basis
--------------
Commercial AI detectors (ZeroGPT, GPTZero, Winston AI, Turnitin) rely on a blend of:

1. **Perplexity** — how surprising each next token is to a language model.
   AI text is usually low-perplexity (statistically smooth / predictable).
2. **Burstiness** — variance of perplexity and sentence length across a document.
   Humans swing between short blunt lines and long multi-clause thoughts; LLMs don't.
3. **Stylometric fingerprints** — banned corporate-AI lexis (delve, tapestry,
   furthermore, paramount…), missing contractions, uniform rhythm, stock transitions.

Agent B (The Critic) is instructed to emulate those signals aggressively.
Agent A (The Writer) is instructed to maximize burstiness + perplexity while
preserving facts and killing the AI lexis ban list.
"""

from __future__ import annotations

from typing import Final, FrozenSet, Tuple

# ---------------------------------------------------------------------------
# Agent B — The Critic (aggressive AI detector persona)
# ---------------------------------------------------------------------------

DETECTOR_RULES: Final[str] = """
You are an advanced, aggressive AI Detector mimicking the proprietary algorithms of ZeroGPT, Winston AI, GPTZero, Originality.ai, and Turnitin.
Analyze the following text deeply. Break it down sentence by sentence.

Look for ALL of the following AI fingerprints:
- Statistical predictability / low token perplexity (safe, generic next-word choices)
- Flat linguistic rhythm (lack of burstiness — uniform sentence length and structure)
- Absence of contractions (do not / cannot / it is instead of don't / can't / it's)
- Heavy usage of AI transition markers and corporate-AI vocabulary
- Overly balanced paragraph structure with identical clause patterns
- Em-dash overuse, rhetorical question stacking, and hollow intensifiers
- Perfect grammar with zero human roughness (no asides, no self-correction, no emphasis)

You MUST respond ONLY with a valid JSON object matching this exact structure:
{
    "overall_ai_percentage": 85.5,
    "flagged_sentences": [
        {
            "sentence": "Furthermore, it is paramount to delve into these metrics.",
            "ai_confidence_score": 98.0,
            "reason_for_flag": "Contains banned AI transition strings 'Furthermore' and 'delve into' with zero structural variance."
        }
    ],
    "is_undetectable": false
}

Scoring guidance:
- overall_ai_percentage is 0.0 (pure human) to 100.0 (pure AI).
- Flag any sentence with ai_confidence_score >= 50.0 in flagged_sentences.
- Set "is_undetectable" to true ONLY if the overall_ai_percentage is below 10%.
- Be aggressive: if the prose is smooth, generic, or formulaic, score it high.

Do not return markdown blocks or backticks. Return raw JSON only.
"""

# ---------------------------------------------------------------------------
# Agent A — The Writer (human style guide)
# ---------------------------------------------------------------------------

HUMANIZER_RULES: Final[str] = """
ROLE: Elite investigative journalist and professional linguist. Your objective is to rewrite the text to completely mimic natural human speech patterns, bypassing advanced AI detectors (ZeroGPT, Winston, GPTZero, Turnitin, Originality.ai).

CORE ARCHITECTURAL DIRECTIVES:
1. MAXIMIZE STRUCTURAL BURSTINESS: Intentionally vary sentence lengths dramatically. Pair a short, blunt sentence (3–6 words) directly with a sweeping multi-clause sentence (25–35 words). Never let three consecutive sentences share a similar length band.
2. MAXIMIZE TOKEN PERPLEXITY: Avoid statistically predictable next words. Prefer sharp, contextually rich phrasing over safe corporate English. Occasional idiom, concrete detail, or unexpected verb is good.
3. HUMAN STYLOMETRIC FLOW: Use natural contractions ("don't", "can't", "it's", "you'll", "we're"). Use conversational transitions. Allow mild asides, emphasis, and imperfect rhythm — humans are uneven on purpose.
4. ABSOLUTE ZERO-TOLERANCE BAN LIST: Never use: delve, tapestry, testament, revolutionize, furthermore, moreover, paramount, catalyst, dynamic, paradigm, looking ahead, in conclusion, in today's world, it is important to note, nestled, vibrant, groundbreaking, leverage (as verb fluff), underscore, landscape (metaphorical), pivotal, realm, embark, foster, enhance, comprehensive, robust (as filler), seamlessly, cutting-edge, game-changer, navigate (metaphorical fluff), multifaceted, interplay, utilize (prefer "use").
5. CONTEXT PRESERVATION: Retain 100% of the original factual accuracy, numbers, names, claims, and SEO keywords. Do not invent facts. Do not drop critical meaning.
6. OUTPUT RULES: Return ONLY the rewritten document as plain text. No preamble, no "Here is the rewrite", no markdown fences, no score commentary.
"""

# ---------------------------------------------------------------------------
# Expanded ban list used by local heuristics (case-insensitive matching)
# ---------------------------------------------------------------------------

AI_BAN_PHRASES: Final[Tuple[str, ...]] = (
    "delve",
    "delve into",
    "tapestry",
    "testament",
    "revolutionize",
    "revolutionise",
    "furthermore",
    "moreover",
    "paramount",
    "catalyst",
    "paradigm",
    "looking ahead",
    "in conclusion",
    "in summary",
    "to summarize",
    "in today's world",
    "in today's digital age",
    "it is important to note",
    "it is worth noting",
    "it is crucial to",
    "nestled",
    "vibrant",
    "groundbreaking",
    "cutting-edge",
    "cutting edge",
    "game-changer",
    "game changer",
    "seamlessly",
    "multifaceted",
    "interplay",
    "underscore",
    "underscores",
    "pivotal",
    "embark",
    "embark on",
    "foster",
    "fostering",
    "leverage",
    "leveraging",
    "utilize",
    "utilizing",
    "utilise",
    "comprehensive overview",
    "robust framework",
    "navigate the",
    "in the realm of",
    "a wide range of",
    "plays a crucial role",
    "serves as a",
    "shed light on",
    "at the end of the day",
    "moving forward",
    "that being said",
    "when it comes to",
    "in order to",
    "due to the fact that",
    "a myriad of",
    "plethora",
)

AI_BAN_WORDS: Final[FrozenSet[str]] = frozenset(
    {
        "delve",
        "tapestry",
        "testament",
        "revolutionize",
        "revolutionise",
        "furthermore",
        "moreover",
        "paramount",
        "catalyst",
        "paradigm",
        "nestled",
        "vibrant",
        "groundbreaking",
        "seamlessly",
        "multifaceted",
        "interplay",
        "underscore",
        "underscores",
        "pivotal",
        "embark",
        "foster",
        "fostering",
        "leverage",
        "leveraging",
        "utilize",
        "utilizing",
        "utilise",
        "plethora",
        "myriad",
        "robust",
        "comprehensive",
        "cutting-edge",
        "game-changer",
    }
)

# Contractions humans use frequently; absence is an AI signal
COMMON_CONTRACTIONS: Final[Tuple[str, ...]] = (
    "don't",
    "doesn't",
    "didn't",
    "can't",
    "couldn't",
    "won't",
    "wouldn't",
    "shouldn't",
    "isn't",
    "aren't",
    "wasn't",
    "weren't",
    "hasn't",
    "haven't",
    "hadn't",
    "it's",
    "that's",
    "there's",
    "here's",
    "what's",
    "who's",
    "you're",
    "we're",
    "they're",
    "i'm",
    "i've",
    "i'll",
    "you'll",
    "we'll",
    "they'll",
    "let's",
)

# Default pipeline knobs
DEFAULT_MODEL: Final[str] = "gpt-4o"
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_TARGET_SCORE: Final[float] = 10.0
DEFAULT_SCAN_TEMPERATURE: Final[float] = 0.1
DEFAULT_MUTATE_TEMPERATURE: Final[float] = 0.82
UNDETECTABLE_THRESHOLD: Final[float] = 10.0
FLAG_CONFIDENCE_THRESHOLD: Final[float] = 50.0
