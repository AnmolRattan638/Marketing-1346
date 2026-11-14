"""Groq keys from several organizations (limits are per organization). Set any of: GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3 ... or GROQ_API_KEYS (comma list).
Every call starts from a different key (random start) so the load spreads; a 429 moves on to the next key at once."""
import os
import random


def keys() -> list[str]:
    found = [os.environ.get("GROQ_API_KEY", "")]
    found += [os.environ.get(f"GROQ_API_KEY_{i}", "") for i in range(2, 10)]
    found += os.environ.get("GROQ_API_KEYS", "").split(",")
    out = list(dict.fromkeys(k.strip() for k in found if k and k.strip()))
    return out


def rotated() -> list[str]:
    ks = keys()
    if len(ks) > 1:
        i = random.randrange(len(ks))
        ks = ks[i:] + ks[:i]
    return ks
