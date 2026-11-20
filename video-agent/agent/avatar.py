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


def energy_of(narration: str | None, fps: int, frames: int) -> list[float]:
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
        g["avatar"] = {"src": poses, "swapAt": swap, "energy": energy_of(built[i].get("narration"), fps, frames)}
    if idx:
        log(f"avatar: masked character in scenes {[built[i]['id'] for i in idx]}")
    return len(idx)


def presenter(built: list, scene_frames: list[int], cfg: dict, fps: int, has_outro: bool) -> dict | None:
    """The permanent presenter: one block for the whole reel (poses, voice loudness for every frame, pose cuts, and where he is hidden). None when switched off.
    The window stays out of the hook (first scene, a full-screen opening), out of the big avatar scenes (he is already there) and out of the logo end."""
    a = cfg.get("avatar") or {}
    if not enabled(cfg) or not a.get("presenter", True):
        return None
    files = stage()
    if not files:
        return None
    energy: list[float] = []
    cuts: list[dict] = []
    hide: list[list[int]] = []
    pose = (date.today().toordinal()) % len(files)
    start = 0
    every = int(float(a.get("pose_seconds", 3.2)) * fps)
    for i, (b, frames) in enumerate(zip(built, scene_frames)):
        energy += energy_of(b.get("narration"), fps, frames)
        g = b.get("graphic") or {}
        if i == 0 or g.get("layout") in ("avatar", "hook"):
            hide.append([start, start + frames])
        for k, f in enumerate(range(0, max(frames, 1), every)):
            if frames - f < fps:                      # no cut in the last second of a scene
                break
            pose = (pose + 1) % len(files) if len(files) > 1 else 0
            cuts.append({"f": start + f, "i": pose})
        start += frames
    if has_outro:
        hide.append([start, start + int(float((cfg.get("look") or {}).get("outro_seconds", 1.8)) * fps) + 5])
    merged: list[list[int]] = []
    for r in hide:                                    # touching ranges become one
        if merged and r[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], r[1])
        else:
            merged.append(r)
    log(f"avatar: presenter window on the whole reel, hidden in {len(merged)} stretch(es), {len(cuts)} pose changes")
    return {"src": files, "energy": energy, "cuts": cuts, "hide": merged}


energy = energy_of            # old name, kept for callers and tests
