import json, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DRAFTS = DATA / "drafts"
MEDIA = DATA / "media"
REPO = (os.getenv("GITHUB_REPOSITORY") or "AnmolRattan638/Marketing-1346")
BRANCH = (os.getenv("GITHUB_REF_NAME") or "main")

# Override any of these with repo Variables / env if the model IDs change.
GEMMA_MODEL = (os.getenv("GEMMA_MODEL") or "gemma-3-27b-it")      # research / images / video (set to the Gemma 4 ID from AI Studio)
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


def services():
    return load_json(ROOT / "config" / "services.json", {})


def voice():
    return read(ROOT / "config" / "voice.md")
