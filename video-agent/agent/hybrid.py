"""The strict hybrid editor. Every scene is cut into short shots; every shot is YOUR raw footage, stock video, or a photo. Code decides, not the model.

Rules (config.json -> "hybrid"; each is checked again by audit() on the finished timeline, and in strict mode a violation stops the run):
  1. Your raw footage fills at least min_raw_share of the screen time (when you have raw clips).
  2. Stock video fills at most max_stock_share of it (when other sources exist).
  3. At least min_photo_shots photos (your own first, otherwise stock photos) when a photo source exists.
  4. No source type three times in a row (max_same_in_row = 2).
  5. The first shot is the hero's first_shot type (default raw): the hook shows YOU, not stock.
  6. Shot lengths stay inside the range measured from your Hero reels (agent/style.py).
  7. When two or more source types exist, at least two are used.
The model only writes the story and a search query per scene; it never picks the source.
"""
from __future__ import annotations

import random
import subprocess
from datetime import date
from pathlib import Path

from . import edits, footage
from .common import log, media_duration, run

W, H, FPS = 1080, 1920, 30
DEFAULTS = {"strict": True, "min_raw_share": 0.4, "max_stock_share": 0.45, "min_photo_shots": 1, "max_same_in_row": 2, "fade_seconds": 0.2}
TYPES = ("raw", "stock", "photo")


class HybridError(RuntimeError):
    pass


def settings(cfg: dict) -> dict:
    return {**DEFAULTS, **(cfg.get("hybrid") or {})}


# ---------- 1. cutting a scene into shots ----------
def split_scene(seconds: float, prof: dict, rng: random.Random) -> list[float]:
    n = max(1, round(seconds / prof["shot_median"]))
    while n > 1 and seconds / n < prof["shot_min"]:
        n -= 1
    while seconds / n > prof["shot_max"]:
        n += 1
    w = [rng.uniform(0.85, 1.15) for _ in range(n)]
    return [seconds * x / sum(w) for x in w]


# ---------- 2. deciding the source of every shot ----------
def allocate(durs: list[float], avail: dict, hs: dict, prof: dict, rng: random.Random) -> list[str]:
    """Greedy by time deficit, with the run limit and the stock cap enforced while choosing."""
    types = [t for t in TYPES if avail.get(t)]
    if not types:
        raise HybridError("no footage source is available (no raw clips, no stock key, no photos)")
    total = sum(durs)
    want = {"raw": 0.5, "stock": 0.3, "photo": 0.2}
    want = {t: want[t] for t in types}
    if "raw" in want:
        want["raw"] = max(want["raw"], hs["min_raw_share"] + 0.05)
    if "stock" in want and len(types) > 1:
        want["stock"] = min(want["stock"], hs["max_stock_share"] - 0.05)
    norm = sum(want.values())
    want = {t: v / norm * total for t, v in want.items()}
    got = {t: 0.0 for t in types}
    out: list[str] = []
    photos_needed = hs["min_photo_shots"] if "photo" in types else 0
    for i, d in enumerate(durs):
        left = len(durs) - i
        ok = list(types)
        if len(out) >= hs["max_same_in_row"] and len(set(out[-hs["max_same_in_row"]:])) == 1:
            ok = [t for t in ok if t != out[-1]] or ok
        if "stock" in ok and len(ok) > 1 and (got["stock"] + d) / total > hs["max_stock_share"]:
            ok.remove("stock")
        if i == 0 and prof.get("first_shot") in ok:
            pick = prof["first_shot"]
        elif photos_needed and out.count("photo") < photos_needed and left <= photos_needed - out.count("photo") and "photo" in ok:
            pick = "photo"
        else:
            pick = max(ok, key=lambda t: (want[t] - got[t]) + rng.uniform(0, 0.01 * total))
        out.append(pick)
        got[pick] += d
    return out


def audit(shots: list[dict], avail: dict, hs: dict, prof: dict) -> list[str]:
    """Check the finished timeline against the rules. Empty list = the reel follows the hybrid."""
    bad: list[str] = []
    total = sum(s["seconds"] for s in shots) or 1.0
    by = {t: sum(s["seconds"] for s in shots if s["type"] == t) for t in TYPES}
    types = [t for t in TYPES if avail.get(t)]
    if avail.get("raw") and by["raw"] / total < hs["min_raw_share"] - 0.02:
        bad.append(f"raw footage is {by['raw'] / total:.0%} of the reel, the rule is at least {hs['min_raw_share']:.0%}")
    if len(types) > 1 and by["stock"] / total > hs["max_stock_share"] + 0.02:
        bad.append(f"stock video is {by['stock'] / total:.0%} of the reel, the rule is at most {hs['max_stock_share']:.0%}")
    if avail.get("photo") and sum(1 for s in shots if s["type"] == "photo") < hs["min_photo_shots"]:
        bad.append(f"fewer than {hs['min_photo_shots']} photo shots")
    run_len = 1
    for a, b in zip(shots, shots[1:]):
        run_len = run_len + 1 if a["type"] == b["type"] else 1
        if len(types) > 1 and run_len > hs["max_same_in_row"]:
            bad.append(f"more than {hs['max_same_in_row']} {b['type']} shots in a row")
            break
    first = prof.get("first_shot", "raw")
    if first in TYPES and avail.get(first) and shots and shots[0]["type"] != first:
        bad.append(f"the first shot is {shots[0]['type']}, the rule is {first}")
    if len(types) > 1 and len({s["type"] for s in shots}) < 2:
        bad.append("only one source type used")
    for s in shots:
        if not prof["shot_min"] * 0.6 <= s["seconds"] <= prof["shot_max"] * 1.5:
            bad.append(f"a {s['seconds']:.1f}s shot is outside the {prof['shot_min']}-{prof['shot_max']}s range of your Hero reels")
            break
    return bad


# ---------- 3. choosing the asset for a shot ----------
def _score(tags: set, words: set) -> int:
    return len(tags & words)


def pick_local(items: list[dict], words: set, used: set, rng: random.Random) -> dict | None:
    fresh = [x for x in items if x["name"] not in used] or items
    if not fresh:
        return None
    best = max(_score(x["tags"], words) for x in fresh)
    return rng.choice([x for x in fresh if _score(x["tags"], words) == best])


# ---------- 4. making each shot, then joining ----------
def _fit_filter(landscape: bool) -> str:
    if landscape:   # screen recordings and landscape demos: keep the whole frame on a blurred copy of itself
        return (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:5[bg];"
                f"[b]scale={W}:-2:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"


def _zoom(effect: str, frames: int) -> str:
    if effect == "punch_in":
        z = "1+0.14*min(1,on/9)"
    elif effect == "push_in":
        z = f"1+0.07*on/{max(frames, 1)}"
    else:
        return ""
    return f",zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS}"


def _is_landscape(path: Path) -> bool:
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)], text=True, capture_output=True)
    try:
        w, h = (int(x) for x in p.stdout.strip().split(",")[:2])
        return w > h
    except ValueError:
        return False


def make_shot(shot: dict, dest: Path, rng: random.Random) -> None:
    sec, frames = shot["seconds"], int(round(shot["seconds"] * FPS))
    src: Path = shot["src"]
    if shot["type"] == "photo":
        zoom = "1+0.10*on/%d" % max(frames, 1)
        vf = (f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
              f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},format=yuv420p")
        run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", src, "-vf", vf, "-frames:v", frames, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", dest])
        return
    dur = media_duration(src)
    start = rng.uniform(0, max(0.0, dur - sec - 0.1)) if dur > sec + 0.2 else 0.0
    loop = ["-stream_loop", "-1"] if dur < sec + 0.1 else []
    vf = _fit_filter(shot["type"] == "raw" and _is_landscape(src)) + f",fps={FPS}" + _zoom(shot["effect"], frames) + ",format=yuv420p"
    run(["ffmpeg", "-y", "-loglevel", "error", *loop, "-ss", f"{start:.2f}", "-i", src, "-t", f"{sec:.3f}", "-vf", vf,
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-r", FPS, dest])


def join(parts: list[Path], shots: list[dict], hs: dict, dest: Path) -> None:
    """Hard cuts everywhere except the shots marked 'fade', which cross-dissolve. Shot lengths already include the overlap, so the total is exact."""
    if all(s["transition_in"] == "cut" for s in shots[1:]):
        lst = dest.with_suffix(".txt")
        lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", dest])
        lst.unlink()
        return
    ins = [x for p in parts for x in ("-i", p)]
    chain, cur, length = [], "[0:v]", shots[0]["seconds"]
    for i in range(1, len(parts)):
        f = hs["fade_seconds"] if shots[i]["transition_in"] == "fade" else 0.04
        length_i = length - f
        out = f"[v{i}]"
        chain.append(f"{cur}[{i}:v]xfade=transition=fade:duration={f}:offset={length_i:.3f}{out}")
        cur, length = out, length_i + shots[i]["seconds"]
    run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(chain), "-map", cur, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", dest])


# ---------- 5. the whole reel ----------
class Editor:
    def __init__(self, cfg: dict, offline: bool):
        self.cfg, self.offline, self.hs = cfg, offline, settings(cfg)
        self.rng = random.Random(date.today().toordinal())
        root = None if offline and not edits.configured() else edits.sync()
        self.lib = edits.raw_library(root) if root else {"videos": [], "images": []}
        reels, notes = edits.hero_reels(root) if root else ([], [])
        from . import style
        self.prof = style.profile(reels, notes)
        self.used_local: set = set()
        self.used_stock: set = set()
        self.configured = bool(root)
        self.avail = {"raw": bool(self.lib["videos"]), "stock": offline or footage.stock_available("video"),
                      "photo": offline or bool(self.lib["images"]) or footage.stock_available("photo")}
        if offline and not self.lib["videos"]:
            self._seed_offline()
        log(f"hybrid: raw videos {len(self.lib['videos'])}, raw photos {len(self.lib['images'])}, hero reels measured {self.prof['reels_measured']}, "
            f"shot length {self.prof['shot_min']}-{self.prof['shot_max']}s (median {self.prof['shot_median']}s)")
        if self.hs["strict"] and not offline:
            if not self.configured:
                raise HybridError("the edits folder is not connected (secret EDITS_DRIVE_URL). Strict hybrid mode needs your raw footage, so no reel was made.")
            if not self.avail["raw"]:
                raise HybridError("the edits folder has no raw video clips (put them in the 'raw' subfolder). Strict hybrid mode needs them, so no reel was made.")

    def _seed_offline(self) -> None:
        """Offline tests: pretend the edits folder has 3 landscape raw clips and 2 photos."""
        import tempfile
        d = Path(tempfile.mkdtemp(prefix="edits_offline_"))
        for n in ("website_demo", "chatbot_demo", "desk_setup"):
            self._synthetic("raw", d / f"{n}.mp4", len(n))
            self.lib["videos"].append({"path": d / f"{n}.mp4", "name": f"{n}.mp4", "tags": edits.tags_of(n + ".x")})
        for k, n in enumerate(("portfolio_shot", "team_photo")):
            self._synthetic("photo", d / f"{n}.jpg", k)
            self.lib["images"].append({"path": d / f"{n}.jpg", "name": f"{n}.jpg", "tags": edits.tags_of(n + ".x")})
        self.avail["raw"] = True

    def library_summary(self) -> str:
        names = sorted({t for v in self.lib["videos"] + self.lib["images"] for t in v["tags"]})[:40]
        return ", ".join(names)

    def _synthetic(self, kind: str, dest: Path, i: int) -> None:
        """Offline tests only: fake clips and photos made by ffmpeg."""
        if kind == "photo":
            run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc2=s=1080x1920:d=1,hue=h={i * 40}", "-frames:v", "1", dest])
        else:
            src = "testsrc=s=1920x1080:r=30:d=6" if kind == "raw" else "mandelbrot=s=1080x1920:r=30"
            run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", src, "-t", "6", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast", dest])

    def prepare(self, scenes: list[tuple[str, dict, float]], out_dir: Path) -> None:
        """Plan the WHOLE reel at once (so the share rules apply to the reel, not to each scene): cut, choose sources, fetch assets, audit."""
        durs, owner = [], []
        for sid, sc, seconds in scenes:
            for d in split_scene(seconds, self.prof, self.rng):
                durs.append(d)
                owner.append((sid, sc))
        types = allocate(durs, self.avail, self.hs, self.prof, self.rng)
        trans = self.prof["transitions"]
        shots = [{"type": t, "seconds": d, "src": None, "credit": {}, "effect": "none", "transition_in": "cut", "sid": sid}
                 for t, d, (sid, _) in zip(types, durs, owner)]
        work = out_dir / "shots"
        work.mkdir(parents=True, exist_ok=True)
        for i, (s, (sid, sc)) in enumerate(zip(shots, owner)):
            words = edits.tags_of(sc.get("footage_query", "") + " " + sc.get("narration", "") + ".x")
            self._fill(s, words, sc, work / f"a{i}", i)
        # effects and transitions come from the Hero style, never from the model; a scene's first shot always cuts in
        for i, s in enumerate(shots):
            if i and s["sid"] == shots[i - 1]["sid"] and self.rng.uniform(0, sum(trans.values())) < trans.get("fade", 0):
                s["transition_in"] = "fade"
            if s["type"] != "photo":
                s["effect"] = "punch_in" if self.rng.uniform(0, 100) < self.prof["punch_in"] else ("push_in" if s["type"] == "stock" else "none")
        for i, s in enumerate(shots[:-1]):      # a fade overlaps the next shot, so add the overlap back to keep the scene length exact
            if shots[i + 1]["transition_in"] == "fade":
                s["seconds"] += self.hs["fade_seconds"]
        bad = audit(shots, self.avail, self.hs, self.prof)
        self.violations = bad
        if bad:
            if self.hs["strict"]:
                raise HybridError("the reel breaks the hybrid rules: " + "; ".join(bad))
            log("hybrid rules NOT met (strict is off): " + "; ".join(bad))
        self.shots = shots

    def render_scene(self, sid: str, out_dir: Path) -> dict:
        shots = [s for s in self.shots if s["sid"] == sid]
        work = out_dir / "shots"
        parts = []
        for i, s in enumerate(shots):
            p = work / f"{sid}_n{i}.mp4"
            make_shot(s, p, self.rng)
            parts.append(p)
        dest = out_dir / f"{sid}.mp4"
        join(parts, shots, self.hs, dest)
        return {"path": f"assets/run/footage/{sid}.mp4", "seconds": round(media_duration(dest), 2),
                "credit": {"scene": sid, "source": "hybrid", "shots": [{"type": s["type"], "seconds": round(s["seconds"], 2), "effect": s["effect"],
                                                                      "transition_in": s["transition_in"], **s["credit"]} for s in shots]},
                "shots": [{"type": s["type"], "seconds": s["seconds"]} for s in shots]}

    def _fill(self, s: dict, words: set, scene: dict, base: Path, i: int) -> None:
        """Find the asset for this shot; if a source fails, move the shot to the next source in the same order of preference."""
        order = {"raw": ["raw", "photo", "stock"], "stock": ["stock", "raw", "photo"], "photo": ["photo", "raw", "stock"]}[s["type"]]
        for t in order:
            if not self.avail.get(t):
                continue
            if t == "raw":
                item = pick_local(self.lib["videos"], words, self.used_local, self.rng)
                if item:
                    self.used_local.add(item["name"])
                    s.update(type="raw", src=item["path"], credit={"file": item["name"]})
                    return
            elif t == "photo":
                item = pick_local(self.lib["images"], words, self.used_local, self.rng)
                if item:
                    self.used_local.add(item["name"])
                    s.update(type="photo", src=item["path"], credit={"file": item["name"]})
                    return
                dest = base.with_suffix(".jpg")
                if self.offline:
                    self._synthetic("photo", dest, i)
                    s.update(type="photo", src=dest, credit={"source": "synthetic"})
                    return
                c = footage._stock_photo(scene["footage_query"], dest, self.used_stock)
                if c:
                    s.update(type="photo", src=dest, credit=c)
                    return
            else:
                dest = base.with_suffix(".mp4")
                if self.offline:
                    self._synthetic("stock", dest, i)
                    s.update(type="stock", src=dest, credit={"source": "synthetic"})
                    return
                c = footage._stock_video(scene["footage_query"], dest, self.used_stock)
                if c:
                    s.update(type="stock", src=dest, credit=c)
                    return
        raise HybridError(f"no asset could be found for a {s['type']} shot")
