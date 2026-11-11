"""The strict hybrid editor. Every scene is cut into short shots; every shot is YOUR raw footage, stock video, or a photo. Code decides, not the model.

Rules (config.json -> "hybrid"; each is checked again by audit() on the finished timeline, and in strict mode a violation stops the run):
  1. At least min_raw_shots shots are your own raw footage (default 1; the first shot already is). Each raw shot is the BEST PART of a clip (agent/clipscore.py),
     never the whole file; a clip can be used for several shots with different parts, and with two or more clips the raw shots use at least two of them.
  2. Stock video fills at most max_stock_share of it (when other sources exist).
  3. At least min_photo_shots photos (default 0: photos are mixed in by weight but never forced; set it in config.json to require some).
  4. No source type three times in a row (max_same_in_row = 2).
  5. The first shot is the hero's first_shot type (default raw): the hook shows YOU, not stock.
  6. Shot lengths stay inside the range measured from your Hero reels (agent/style.py).
  7. When two or more source types exist, at least two are used.
  8. A raw clip may only be used for the service it is labelled with (subfolder, notes.txt or file-name prefix), or from raw/general. Unlabelled clips are never used.
The model only writes the story and a search query per scene; it never picks the source.
"""
from __future__ import annotations

import random
import subprocess
from datetime import date
from pathlib import Path

from . import clipscore, edits, footage
from .common import log, media_duration, run

W, H, FPS = 1080, 1920, 30
DEFAULTS = {"strict": True, "min_raw_shots": 1, "max_stock_share": 0.45, "min_photo_shots": 0, "max_same_in_row": 2, "fade_seconds": 0.2}
TYPES = ("raw", "stock", "photo")


class HybridError(RuntimeError):
    pass


def settings(cfg: dict) -> dict:
    return {**DEFAULTS, **(cfg.get("hybrid") or {})}


# ---------- 1. cutting a scene into shots ----------
def split_scene(seconds: float, prof: dict, rng: random.Random, words: list[dict] | None = None) -> list[float]:
    """Cut a scene into shots. With the scene's word timings, every inner cut is moved onto the start of a spoken word (see snap_cuts)."""
    n = max(1, round(seconds / prof["shot_median"]))
    while n > 1 and seconds / n < prof["shot_min"]:
        n -= 1
    while seconds / n > prof["shot_max"]:
        n += 1
    w = [rng.uniform(0.85, 1.15) for _ in range(n)]
    durs = [seconds * x / sum(w) for x in w]
    return snap_cuts(durs, words, prof) if words else durs


CUT_LEAD = 0.03     # a cut lands this much BEFORE the word it introduces, so the picture is already there when the word is heard
SNAP_TOLERANCE = 0.3


def snap_cuts(durs: list[float], words: list[dict], prof: dict, tol: float = SNAP_TOLERANCE) -> list[float]:
    """Move each inner cut to the nearest word start within `tol` seconds, so the picture changes WITH the speech instead of in the middle of a word.
    Shot lengths are kept inside the Hero range and the scene length is unchanged."""
    n = len(durs)
    if n < 2 or not words:
        return durs
    total = sum(durs)
    lo_len, hi_len = prof["shot_min"] * 0.9, prof["shot_max"] * 1.3
    starts = sorted(w["start"] - CUT_LEAD for w in words if 0 < w["start"] < total)
    bounds, prev = [], 0.0
    cum = 0.0
    for k in range(n - 1):
        cum += durs[k]
        lo = prev + lo_len
        hi = min(prev + hi_len, total - (n - 1 - k) * lo_len)
        if k == n - 2:
            lo = max(lo, total - hi_len)
        cands = [t for t in starts if abs(t - cum) <= tol and lo <= t <= hi]
        b = min(cands, key=lambda t: abs(t - cum)) if cands else min(max(cum, lo), hi)
        bounds.append(b)
        prev = b
    edges = [0.0, *bounds, total]
    return [edges[i + 1] - edges[i] for i in range(n)]


# ---------- 2. deciding the source of every shot ----------
def allocate(durs: list[float], avail: dict, hs: dict, prof: dict, rng: random.Random) -> list[str]:
    """Greedy by time deficit, with the run limit and the stock cap enforced while choosing."""
    types = [t for t in TYPES if avail.get(t)]
    if not types:
        raise HybridError("no footage source is available (no raw clips, no stock key, no photos)")
    total = sum(durs)
    want = {"raw": 0.5, "stock": 0.3, "photo": 0.2}
    want = {t: want[t] for t in types}
    if "stock" in want and len(types) > 1:
        want["stock"] = min(want["stock"], hs["max_stock_share"] - 0.05)
    norm = sum(want.values())
    want = {t: v / norm * total for t, v in want.items()}
    got = {t: 0.0 for t in types}
    out: list[str] = []
    need = {"raw": hs["min_raw_shots"] if "raw" in types else 0, "photo": hs["min_photo_shots"] if "photo" in types else 0}
    for i, d in enumerate(durs):
        left = len(durs) - i
        ok = list(types)
        if len(out) >= hs["max_same_in_row"] and len(set(out[-hs["max_same_in_row"]:])) == 1:
            ok = [t for t in ok if t != out[-1]] or ok
        if "stock" in ok and len(ok) > 1 and (got["stock"] + d) / total > hs["max_stock_share"]:
            ok.remove("stock")
        if i == 0 and prof.get("first_shot") in ok:
            pick = prof["first_shot"]
        elif (short := {t: n - out.count(t) for t, n in need.items() if n > out.count(t)}) and left <= sum(short.values()) and any(t in ok for t in short):
            pick = max((t for t in short if t in ok), key=lambda t: short[t])      # the minimums are met before the reel runs out of shots
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
    raw_shots = [s for s in shots if s["type"] == "raw"]
    if avail.get("raw") and len(raw_shots) < hs["min_raw_shots"]:
        bad.append(f"only {len(raw_shots)} raw shot(s), the rule is at least {hs['min_raw_shots']} of your own footage")
    files = {s["credit"]["file"] for s in raw_shots if (s.get("credit") or {}).get("file")}
    if avail.get("raw_clips", 0) >= 2 and len(raw_shots) >= 2 and len(files) == 1:
        bad.append("every raw shot comes from one clip, the rule is to use at least 2 of your clips")
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


def pick_local(items: list[dict], words: set, used: set, rng: random.Random, service: str = "general") -> dict | None:
    own = [x for x in items if x.get("service") == service and x["name"] not in used]
    fresh = own or [x for x in items if x["name"] not in used] or items      # the service's own clips first, then general, then reuse
    if not fresh:
        return None
    best = max(_score(x["tags"], words) for x in fresh)
    return rng.choice([x for x in fresh if _score(x["tags"], words) == best])


def pick_raw(items: list[dict], words: set, uses: dict, rng: random.Random, service: str = "general") -> dict | None:
    """The clip with the FEWEST shots so far (so every clip is used before any is reused), then the service's own clips, then the best tag match."""
    if not items:
        return None
    best = min((uses.get(x["name"], 0), 0 if x.get("service") == service else 1, -_score(x["tags"], words), rng.random(), i) for i, x in enumerate(items))
    return items[best[-1]]


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
    start = shot.get("start")
    if start is None:     # stock clips (and raw clips that could not be analysed): a random slice
        start = rng.uniform(0, max(0.0, dur - sec - 0.1)) if dur > sec + 0.2 else 0.0
    loop = ["-stream_loop", "-1"] if dur < sec + 0.1 else []
    vf = _fit_filter(shot["type"] == "raw" and _is_landscape(src)) + f",fps={FPS}" + _zoom(shot["effect"], frames) + ",format=yuv420p"
    run(["ffmpeg", "-y", "-loglevel", "error", *loop, "-ss", f"{start:.2f}", "-i", src, "-t", f"{sec:.3f}", "-vf", vf,
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-r", FPS, dest])


def _xfade(parts: list[Path], durs: list[float], f: float, dest: Path) -> None:
    ins = [x for p in parts for x in ("-i", p)]
    chain, cur, length = [], "[0:v]", durs[0]
    for i in range(1, len(parts)):
        length -= f
        out = f"[v{i}]"
        chain.append(f"{cur}[{i}:v]xfade=transition=fade:duration={f}:offset={length:.3f}{out}")
        cur, length = out, length + durs[i]
    run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(chain), "-map", cur, "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "22", "-pix_fmt", "yuv420p", "-r", FPS, dest])


def join(parts: list[Path], shots: list[dict], hs: dict, dest: Path) -> None:
    """Hard cuts, except shots marked 'fade' which cross-dissolve with the shot before them. Shot lengths already include the overlap, so the total is exact.
    Runs of faded shots are dissolved first, then the runs are joined with plain cuts."""
    groups: list[list[int]] = []
    for i, s in enumerate(shots):
        if i and s["transition_in"] == "fade":
            groups[-1].append(i)
        else:
            groups.append([i])
    segs = []
    for g in groups:
        if len(g) == 1:
            segs.append(parts[g[0]])
        else:
            seg = dest.with_name(f"{dest.stem}_seg{g[0]}.mp4")
            _xfade([parts[i] for i in g], [shots[i]["seconds"] for i in g], hs["fade_seconds"], seg)
            segs.append(seg)
    lst = dest.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in segs), encoding="utf-8")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
         "-pix_fmt", "yuv420p", "-r", FPS, dest])
    lst.unlink()


# ---------- 5. the whole reel ----------
class Editor:
    def __init__(self, cfg: dict, offline: bool, service: str = "general"):
        self.cfg, self.offline, self.hs, self.service = cfg, offline, settings(cfg), service
        self.rng = random.Random(date.today().toordinal())
        root = None if offline and not edits.configured() else edits.sync()
        full = edits.raw_library(root) if root else {"videos": [], "images": []}
        self.unassigned = [x["name"] for k in full for x in full[k] if x["service"] == "unassigned"]
        ok = {service, "general"}
        self.lib = {k: [x for x in full[k] if x["service"] in ok] for k in full}      # the only clips this reel may ever touch
        self.others = sum(1 for k in full for x in full[k] if x["service"] not in ok | {"unassigned"})
        reels, notes = edits.hero_reels(root) if root else ([], [])
        from . import style
        self.prof = style.profile(reels, notes)
        self.used_local: set = set()
        self.raw_uses: dict[str, int] = {}                          # shots per raw clip so far
        self.taken: dict[str, list[tuple[float, float]]] = {}       # parts of each raw clip already used
        self.used_stock: set = set()
        self.configured = bool(root)
        self.avail = {"raw": bool(self.lib["videos"]), "raw_clips": len(self.lib["videos"]), "stock": offline or footage.stock_available("video"),
                      "photo": offline or bool(self.lib["images"]) or footage.stock_available("photo")}
        if offline and not self.lib["videos"]:
            self._seed_offline()
        if self.unassigned:
            log(f"hybrid: {len(self.unassigned)} raw file(s) have no service label and are never used: {', '.join(self.unassigned[:6])}")
        log(f"hybrid: service '{service}': raw videos {len(self.lib['videos'])}, raw photos {len(self.lib['images'])} ({self.others} belong to other services), hero reels measured {self.prof['reels_measured']}, "
            f"shot length {self.prof['shot_min']}-{self.prof['shot_max']}s (median {self.prof['shot_median']}s)")
        if self.hs["strict"] and not offline:
            if not self.configured:
                raise HybridError("the edits folder is not connected (secret EDITS_DRIVE_URL). Strict hybrid mode needs your raw footage, so no reel was made.")
            if not self.avail["raw"]:
                raise HybridError(f"no raw video clip is labelled for '{service}' or 'general'. Put clips in edits/raw/{service}/ (or edits/raw/general/ for clips that fit any service), "
                                  f"or name them {service}_something.mp4. {len(self.unassigned)} unlabelled file(s) are ignored. Strict mode needs your clips, so no reel was made.")

    def _seed_offline(self) -> None:
        """Offline tests: pretend the edits folder has 3 landscape raw clips and 2 photos."""
        import tempfile
        d = Path(tempfile.mkdtemp(prefix="edits_offline_"))
        for n in ("website_demo", "chatbot_demo", "desk_setup"):
            self._synthetic("raw", d / f"{n}.mp4", len(n))
            self.lib["videos"].append({"path": d / f"{n}.mp4", "name": f"{n}.mp4", "tags": edits.tags_of(n + ".x"), "service": self.service})
        for k, n in enumerate(("portfolio_shot", "team_photo")):
            self._synthetic("photo", d / f"{n}.jpg", k)
            self.lib["images"].append({"path": d / f"{n}.jpg", "name": f"{n}.jpg", "tags": edits.tags_of(n + ".x"), "service": "general"})
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

    def prepare(self, scenes: list[tuple[str, dict, float]], out_dir: Path, words_by_scene: dict[str, list[dict]] | None = None) -> None:
        """Plan the WHOLE reel at once (so the share rules apply to the reel, not to each scene): cut on the speech, choose sources, fetch assets, audit.
        words_by_scene maps a scene id to its word timings (seconds from the scene start); without them cuts are placed by rhythm only."""
        words_by_scene = words_by_scene or {}
        durs, owner, t0s = [], [], []
        for sid, sc, seconds in scenes:
            t = 0.0
            for d in split_scene(seconds, self.prof, self.rng, words_by_scene.get(sid)):
                durs.append(d)
                owner.append((sid, sc))
                t0s.append(t)
                t += d
        types = allocate(durs, self.avail, self.hs, self.prof, self.rng)
        trans = self.prof["transitions"]
        shots = [{"type": t, "seconds": d, "src": None, "credit": {}, "effect": "none", "transition_in": "cut", "sid": sid, "t0": t0}
                 for t, d, t0, (sid, _) in zip(types, durs, t0s, owner)]
        work = out_dir / "shots"
        work.mkdir(parents=True, exist_ok=True)
        broll_n: dict[str, int] = {}
        for i, (s, (sid, sc)) in enumerate(zip(shots, owner)):
            query = sc.get("footage_query", "")
            if s["type"] != "raw" and sc.get("broll"):       # each cutaway shows what is being said at that moment, not the same search again
                k = broll_n.get(sid, 0)
                broll_n[sid] = k + 1
                query = sc["broll"][k % len(sc["broll"])]
            spoken = " ".join(w["text"] for w in words_by_scene.get(sid, []) if s["t0"] - 0.05 <= w["start"] < s["t0"] + s["seconds"])
            words = edits.tags_of(query + " " + (spoken or sc.get("narration", "")) + ".x")
            s["query"] = query
            self._fill(s, words, {**sc, "footage_query": query}, work / f"a{i}", i)
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
        for s in shots:
            if s["type"] in ("raw", "photo") and s["credit"].get("service") not in (None, self.service, "general"):
                bad.append(f"a raw clip labelled '{s['credit']['service']}' was used in a '{self.service}' reel")
        self.violations = bad
        parts = [f"{s['credit']['file']}@{s['credit']['start']}s" for s in shots if s["type"] == "raw" and s["credit"].get("file")]
        log(f"hybrid: {len(parts)} raw shot(s) from {len({p.split('@')[0] for p in parts})} clip(s): {', '.join(parts)}")
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
        cuts = [{"at": round(s["t0"], 3), "kind": s["transition_in"], "type": s["type"], "effect": s["effect"]} for s in shots[1:]]
        return {"path": f"assets/run/footage/{sid}.mp4", "seconds": round(media_duration(dest), 2), "cuts": cuts,
                "credit": {"scene": sid, "source": "hybrid", "shots": [{"type": s["type"], "seconds": round(s["seconds"], 2), "effect": s["effect"],
                                                                      "transition_in": s["transition_in"], **s["credit"]} for s in shots]},
                "shots": [{"type": s["type"], "seconds": s["seconds"]} for s in shots]}

    def _best_part(self, item: dict, need: float) -> float | None:
        """Start of the best part of this clip for a shot of `need` seconds, avoiding parts earlier shots already used. None = use a random slice."""
        dur = media_duration(item["path"])
        if dur <= need:
            return 0.0                                  # shorter than the shot: the whole clip (looped by make_shot)
        taken = self.taken.setdefault(item["name"], [])
        start = clipscore.best_start(item["path"], need, dur, taken)
        if start is not None:
            taken.append((start, start + need))
        return start

    def _fill(self, s: dict, words: set, scene: dict, base: Path, i: int) -> None:
        """Find the asset for this shot; if a source fails, move the shot to the next source in the same order of preference."""
        order = {"raw": ["raw", "photo", "stock"], "stock": ["stock", "raw", "photo"], "photo": ["photo", "raw", "stock"]}[s["type"]]
        for t in order:
            if not self.avail.get(t):
                continue
            if t == "raw":
                item = pick_raw(self.lib["videos"], words, self.raw_uses, self.rng, self.service)
                if item:
                    self.raw_uses[item["name"]] = self.raw_uses.get(item["name"], 0) + 1
                    start = self._best_part(item, s["seconds"] + self.hs["fade_seconds"] + 0.1)      # room for a fade overlap
                    s.update(type="raw", src=item["path"], start=start, credit={"file": item["name"], "service": item["service"], "start": round(start or 0, 2)})
                    return
            elif t == "photo":
                item = pick_local(self.lib["images"], words, self.used_local, self.rng, self.service)
                if item:
                    self.used_local.add(item["name"])
                    s.update(type="photo", src=item["path"], credit={"file": item["name"], "service": item["service"]})
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
