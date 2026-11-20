"""The masked avatar. Picks which spoken scenes show the character, which pose, and measures how loud the voice is on every frame so the glow and
the breathing follow the narration (the mouth is covered, so no lip-sync is needed). Pure CPU: no GPU, no paid service."""
import array
import shutil
import subprocess
from datetime import date

from .common import ROOT, WORK, log

POSES = 4
PLAIN = ("title", "punch")          # heading-only scenes that the character can take over without hiding a picture


def enabled(cfg: dict) -> bool:
    a = cfg.get("avatar") or {}
    return bool(a.get("enabled")) and len(list((ROOT / "assets" / "avatar").glob("pose*.jpg"))) >= 1


def stage() -> list[str]:
    (WORK / "avatar").mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted((ROOT / "assets" / "avatar").glob("pose*.jpg")):
        shutil.copy(p, WORK / "avatar" / p.name)
        out.append(f"assets/run/avatar/{p.name}")
    return out


def energy(narration: str | None, fps: int, frames: int) -> list[float]:
    """Loudness 0..1 per video frame from the scene's narration file (zeros if it cannot be read)."""
    if not narration:
        return [0.0] * frames
    try:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(narration), "-f", "f32le", "-ac", "1", "-ar", "8000", "-"],
                             capture_output=True, timeout=60).stdout
        a = array.array("f"); a.frombytes(raw[: len(raw) // 4 * 4])
        step = 8000 // fps
        env = []
        for i in range(frames):
            seg = a[i * step:(i + 1) * step]
            env.append((sum(x * x for x in seg) / len(seg)) ** 0.5 if seg else 0.0)
        top = sorted(env)[int(len(env) * 0.95)] if env else 0
        top = top or 1e-6
        return [round(min(1.0, x / top), 3) for x in env]
    except Exception as e:
        log(f"avatar: could not measure the voice ({e}); the glow stays still")
        return [0.0] * frames


def choose(graphics: list, cfg: dict) -> list[int]:
    """Indexes of the scenes that become avatar scenes: plain heading scenes, never the hook (first) or the last scene, spread across the reel."""
    a = cfg.get("avatar") or {}
    ok = [i for i, g in enumerate(graphics) if 0 < i < len(graphics) - 1 and (g or {}).get("layout") in PLAIN]
    want = int(a.get("max_scenes", 3))
    if len(ok) <= want:
        return ok
    step = len(ok) / want
    return [ok[int(k * step)] for k in range(want)]


def apply(built: list, cfg: dict, fps: int, frames_of) -> int:
    """Turn the chosen scenes into layout 'avatar'. Returns how many were changed."""
    if not enabled(cfg):
        return 0
    files = stage()
    if not files:
        return 0
    idx = choose([b.get("graphic") for b in built], cfg)
    base = date.today().toordinal()
    for n, i in enumerate(idx):
        g = built[i]["graphic"]
        frames = frames_of(built[i])
        first = (base + n * 2) % len(files)
        poses = [files[first]]
        swap = None
        if frames / fps > 4.0:                         # a long scene changes pose half-way, like a cut to another camera angle
            poses.append(files[(first + 1) % len(files)])
            swap = round(frames / fps / 2, 2)
        g["layout"] = "avatar"
        g["avatar"] = {"src": poses, "swapAt": swap, "energy": energy(built[i].get("narration"), fps, frames)}
    if idx:
        log(f"avatar: masked character in scenes {[built[i]['id'] for i in idx]}")
    return len(idx)
