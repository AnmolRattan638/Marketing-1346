import json, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DRAFTS = DATA / "drafts"
MEDIA = DATA / "media"
REPO = (os.getenv("GITHUB_REPOSITORY") or "AnmolRattan638/Marketing-1346")
BRANCH = (os.getenv("GITHUB_REF_NAME") or "main")

# Override any of these with repo Variables / env if the model IDs change.
GEMMA_MODEL = (os.getenv("GEMMA_MODEL") or "gemma-4-31b-it")      # research / images / video (set to the Gemma 4 ID from AI Studio)
GROQ_MODEL = (os.getenv("GROQ_MODEL") or "openai/gpt-oss-120b")    # analysis, fact-check, strategist
GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "gemini-3.5-flash")   # final post writing

NVIDIA_MODEL = (os.getenv("NVIDIA_MODEL") or "nvidia/nemotron-3-ultra-550b-a55b:free")   # strategist. A ":free" ID is OpenRouter-style and is called via OpenRouter
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL") or ""   # empty = pick a currently-free model automatically

PLATFORMS = ["instagram", "linkedin", "bluesky"]


def read(path):
    return pathlib.Path(path).read_text(encoding="utf-8")


def load_json(path, default):
    try:
        return json.loads(read(path))
    except Exception:
        return default


def save_json(path, obj):
    pathlib.Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def history():
    """Posting history for the agents: history.json merged with every saved draft, one entry per (date, topic).
    Drafts that were rejected by hand-editing the draft file, or never tapped, still count as 'topic already used',
    and so does a rejected draft that was replaced by a new one on the same day."""
    merged = {}
    for h in load_json(DATA / "history.json", []):
        if isinstance(h, dict) and h.get("date"):
            merged[(h["date"], h.get("topic") or "")] = h
    for f in sorted(pathlib.Path(DRAFTS).glob("*.json")):
        d = load_json(f, None)
        if isinstance(d, dict) and d.get("date"):
            merged[(d["date"], d.get("topic") or "")] = {"date": d["date"], "service": d.get("service"), "topic": d.get("topic"),
                                                         "hook_style": d.get("hook_style"), "status": d.get("status"),
                                                         "idea_id": d.get("idea_id")}
    return [merged[k] for k in sorted(merged)]


def services():
    return load_json(ROOT / "config" / "services.json", {})


def voice():
    return read(ROOT / "config" / "voice.md")
