import json, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DRAFTS = DATA / "drafts"
MEDIA = DATA / "media"
REPO = os.getenv("GITHUB_REPOSITORY", "AnmolRattan638/Marketing-1346")
BRANCH = os.getenv("GITHUB_REF_NAME", "main")

# Override any of these with repo Variables / env if the model IDs change.
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-3-27b-it")      # research / images / video (set to the Gemma 4 ID from AI Studio)
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")    # analysis, fact-check, strategist
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")   # final post writing

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
