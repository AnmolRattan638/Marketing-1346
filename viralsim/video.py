"""Video analysis: measure a rendered reel with ffmpeg, run a crowd of viewer bots over it, and name the weak points.

Pipeline (offline, numpy + ffmpeg, no API calls):
  measure():  per-second motion, cuts, on-screen graphic density, voice level and silence from the real file.
  simulate(): viewer bots (personas sampled from the 50k audience pool, each with own patience / sound habit / boredom speed)
              watch second by second; boredom builds when nothing new happens, and viewers leave.
  weak_points(): where retention drops and why, mapped to scenes, each with a concrete fix.
  analyze_video(): everything above + a score and a worth-posting verdict. feedback() turns it into text for a video planner.
The model is a heuristic (see "Read this before trusting a number" in README): it ranks and explains, it does not forecast real views."""
from __future__ import annotations

import json
import math
import re
import subprocess

import numpy as np

SIZE = (54, 96)                    # w, h of the analysis frames
FPS = 2
PERSONAS = {                       # share, base leave-rate/s, extra leave-rate in first 3 s, boredom speed, sound-on chance, weight of info density
    "scroller":  dict(share=0.28, h0=0.040, early=0.10, bore=0.50, sound=0.35, info=0.15, about="impatient: gives a reel 2 seconds"),
    "owner":     dict(share=0.22, h0=0.030, early=0.05, bore=0.30, sound=0.75, info=0.30, about="busy shop owner: stays if it is about his problem"),
    "skeptic":   dict(share=0.14, h0=0.040, early=0.06, bore=0.40, sound=0.60, info=0.30, about="distrusts hype: leaves when nothing concrete shows"),
    "learner":   dict(share=0.12, h0=0.020, early=0.03, bore=0.20, sound=0.80, info=0.40, about="patient: wants steps and explanations"),
    "commuter":  dict(share=0.14, h0=0.030, early=0.06, bore=0.35, sound=0.05, info=0.30, about="watches muted: only picture and text keep him"),
    "binger":    dict(share=0.10, h0=0.020, early=0.04, bore=0.70, sound=0.60, info=0.20, about="loves pace: hates any static stretch"),
}


def _run(cmd: list[str], binary: bool = True):
    p = subprocess.run(cmd, capture_output=True, timeout=300)
    return p.stdout if binary else p.stderr.decode("utf-8", "ignore")


def probe(path: str) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, timeout=60).stdout
    info = json.loads(out or "{}")
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    return {"duration": float((info.get("format") or {}).get("duration") or 0.0), "width": v.get("width"), "height": v.get("height"),
            "has_audio": any(s.get("codec_type") == "audio" for s in info.get("streams", []))}


def frames(path: str) -> np.ndarray:
    w, h = SIZE
    raw = _run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={FPS},scale={w}:{h},format=gray", "-f", "rawvideo", "-"])
    n = len(raw) // (w * h)
    return np.frombuffer(raw[: n * w * h], dtype=np.uint8).reshape(n, h, w).astype(np.float32)


def audio(path: str, sr: int = 8000) -> np.ndarray:
    raw = _run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"])
    return np.frombuffer(raw[: len(raw) // 2 * 2], dtype=np.int16).astype(np.float32) / 32768.0


def cuts(path: str, thr: float = 0.30) -> list[float]:
    err = _run(["ffmpeg", "-v", "info", "-i", str(path), "-vf", f"select='gt(scene,{thr})',showinfo", "-an", "-f", "null", "-"], binary=False)
    return [float(x) for x in re.findall(r"pts_time:([0-9.]+)", err)]


def measure(path: str) -> dict:
    """-> per-second arrays: motion 0-1, cuts (count), info 0-1 (graphic/text density), voice 0-1, plus first-frame stats."""
    meta = probe(path)
    dur = max(meta["duration"], 0.1)
    secs = max(1, int(math.ceil(dur)))
    fr = frames(path)
    motion = np.zeros(secs)
    info = np.zeros(secs)
    if len(fr) > 1:
        d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))                  # change between frames, per half second
        for i, v in enumerate(d):
            s = min(secs - 1, int((i + 1) / FPS))
            motion[s] = max(motion[s], v)
    band = fr[:, 20:76, :] if len(fr) else np.zeros((0, 56, SIZE[0]))
    for i in range(len(band)):
        s = min(secs - 1, int(i / FPS))
        info[s] = max(info[s], float(np.abs(np.diff(band[i], axis=1)).mean()))
    if secs > 1 and motion[0] == 0:
        motion[0] = motion[1]
    cut_t = cuts(path)
    cut_n = np.zeros(secs)
    for t in cut_t:
        cut_n[min(secs - 1, int(t))] += 1
    voice = np.zeros(secs)
    a = audio(path) if meta["has_audio"] else np.zeros(0)
    if len(a):
        for s in range(secs):
            seg = a[s * 8000:(s + 1) * 8000]
            voice[s] = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
    first = fr[0] if len(fr) else np.zeros((SIZE[1], SIZE[0]))
    return {"meta": meta, "seconds": secs, "motion": np.clip(motion / 12.0, 0, 1), "cuts": cut_n, "cut_times": cut_t,
            "info": np.clip(info / 25.0, 0, 1), "voice": voice, "voiced": (voice > 0.015).astype(float),
            "first_contrast": float(first.std() / 64.0), "first_edges": float(np.abs(np.diff(first, axis=1)).mean() / 25.0)}


def _stimulus(m: dict, sound: np.ndarray, info_w: np.ndarray) -> np.ndarray:
    """(viewers, seconds): how much new there is for each viewer each second (0-1)."""
    mo, cu, inf, vo = m["motion"][None, :], np.minimum(1.0, m["cuts"] * 0.8)[None, :], m["info"][None, :], m["voiced"][None, :]
    on = 0.30 * mo + 0.25 * cu + (0.10 + 0.5 * info_w[:, None] * 0.3) * inf + 0.30 * vo
    off = 0.40 * mo + 0.30 * cu + (0.20 + 0.5 * info_w[:, None]) * inf
    return np.clip(np.where(sound[:, None] > 0.5, on, off) * 1.6, 0, 1)


def simulate(m: dict, n: int = 600, seed: int = 0, pool=None) -> dict:
    """Viewer bots watch second by second. -> {"curve": [share still watching at each second], "bots": {persona: {...}}}."""
    rng = np.random.default_rng(seed)
    names = list(PERSONAS)
    pick = rng.choice(len(names), size=n, p=[PERSONAS[k]["share"] for k in names])
    P = {k: np.array([PERSONAS[names[i]][k] for i in pick]) for k in ("h0", "early", "bore", "sound", "info")}
    sound = (rng.random(n) < P["sound"]).astype(float)
    mult = np.ones(n)
    try:                                                                   # the real audience pool tells how patient each sampled person is
        pool = pool or __import__("viralsim.pipeline", fromlist=["default_pool"]).default_pool()
        r = pool.props[rng.integers(0, len(pool), size=n), 0]
        mult = np.clip(1.4 - 0.8 * r, 0.5, 1.6)
    except Exception:
        pass
    secs = m["seconds"]
    stim = _stimulus(m, sound, P["info"])
    alive, bored = np.ones(n, bool), np.zeros(n)
    left_at = np.full(n, float(secs))
    curve = []
    for t in range(secs):
        curve.append(float(alive.mean()))
        s = stim[:, t]
        bored = np.where(s < 0.28, bored + P["bore"] * (0.28 - s) / 0.28 * 1.4, np.maximum(0.0, bored - 0.5 * s))
        h = (P["h0"] + (P["early"] if t < 3 else 0.0)) * (1.0 + 1.8 * bored) * mult
        gone = alive & (rng.random(n) < 1 - np.exp(-h))
        left_at[gone] = t + 0.5
        alive &= ~gone
    curve.append(float(alive.mean()))
    bots = {}
    for i, k in enumerate(names):
        sel = pick == i
        if not sel.any():
            continue
        avg = float(np.mean(left_at[sel] / secs))
        med = float(np.median(left_at[sel]))
        bots[k] = {"about": PERSONAS[k]["about"], "n": int(sel.sum()), "avg_watch": round(avg, 2), "finish": round(float(np.mean(left_at[sel] >= secs)), 2),
                   "median_leaves_at": round(med, 1), "sound_on": round(float(sound[sel].mean()), 2),
                   "verdict": "stays" if avg >= 0.62 else "drifts" if avg >= 0.40 else "leaves"}
    return {"curve": curve, "bots": bots, "avg_watch": float(np.mean(left_at / secs)), "finish": float(np.mean(left_at >= secs)),
            "hold3": float(curve[min(3, len(curve) - 1)]), "sound_off_hold": _hold(left_at, sound < 0.5, secs)}


def _hold(left_at, sel, secs) -> float:
    return float(np.mean(left_at[sel] / secs)) if sel.any() else 0.0


def _scene_at(spans: list[dict], t: float) -> dict | None:
    return next((s for s in spans if s["start"] <= t < s["end"] + 0.001), spans[-1] if spans else None)


def weak_points(m: dict, sim: dict, spans: list[dict] | None = None) -> list[dict]:
    """Ranked list of {t, kind, severity 0-1, scene, beat, detail, fix, planner}: planner=True when the video planner can fix it with picture/fx/camera/sfx."""
    spans, out, secs = spans or [], [], m["seconds"]
    curve = sim["curve"]

    def add(t, kind, sev, detail, fix, planner=True):
        sc = _scene_at(spans, t)
        out.append({"t": round(float(t), 1), "kind": kind, "severity": round(float(min(1.0, sev)), 2), "scene": (sc or {}).get("id"), "beat": (sc or {}).get("beat"),
                    "detail": detail, "fix": fix, "planner": planner})

    if sim["hold3"] < 0.75:                                                    # the first three seconds lose too many viewers
        add(0, "hook_leaks", (0.75 - sim["hold3"]) * 3, f"only {sim['hold3']:.0%} are still watching at 3s",
            "frame 1 needs more motion: a punch slide with a fast zoom/shake on the headline, a hard cut or stat pop inside the first 2 seconds, and a high-contrast ghost word")
    if m["first_contrast"] < 0.25:
        add(0, "flat_first_frame", 0.5, "the first frame is low contrast", "use a full-colour punch slide with a big bold headline for scene 1")
    run0 = None
    for t in range(secs):                                                     # static runs: no cut, little motion
        quiet = m["motion"][t] < 0.12 and m["cuts"][t] == 0
        if quiet and run0 is None:
            run0 = t
        if (not quiet or t == secs - 1) and run0 is not None:
            end = t if not quiet else t + 1
            if end - run0 >= 3:
                add(run0, "static_stretch", 0.25 + 0.12 * (end - run0), f"{end - run0}s with almost no motion or cut ({run0}-{end}s)",
                    "add a pattern reset every 2 seconds here: change the graphic layout, add a zoom/pulse on the key word, a stat chip, an arrow or a highlight, and a soft sfx on the change")
            run0 = None
    dead = [t for t in range(1, secs - 1) if m["voiced"][t] == 0 and m["motion"][t] < 0.2]
    if dead:                                                                   # one finding for the whole silent stretch, not one per second
        add(dead[0], "dead_air", min(0.7, 0.2 + 0.08 * len(dead)), f"{len(dead)}s of silence with little on screen (first at {dead[0]}s)",
            "tighten the gap with a transition sfx and a visual change on the silent seconds")
    lows = [t for t in range(secs) if m["info"][t] < 0.08 and t < secs - 1]
    if len(lows) >= 3:
        add(lows[0], "empty_frames", 0.3, f"{len(lows)} seconds with almost no text or graphic (first at {lows[0]}s)",
            "put a keyword label, a step badge or a stat on every scene so a muted viewer still gets the point")
    drops = np.diff(curve)
    if len(drops):
        thr = max(0.045, float(np.median(-drops)) * 2.2)
        for t in np.argsort(drops)[:3]:
            if -drops[t] > thr and t >= 3:
                add(t, "cliff", min(1.0, -drops[t] * 8), f"{-drops[t]:.0%} of viewers leave around {t}-{t + 1}s",
                    f"something must happen just before {t}s: a re-hook (a question or contrast on screen), a layout change or a stat reveal")
    if m["seconds"] > 75:
        add(m["seconds"] - 1, "too_long", 0.4, f"{m['seconds']}s is long for a Reel", "shorten the script (words, not the planner)", planner=False)
    if m["seconds"] >= 6 and sim["curve"][-2] > 0 and sim["finish"] < 0.12:
        add(m["seconds"] - 2, "weak_ending", 0.3, f"only {sim['finish']:.0%} reach the end", "end on a loop back to the hook's image and show the CTA as a bold slide", True)
    return sorted(out, key=lambda w: -w["severity"])


def analyze_video(path: str, spans: list[dict] | None = None, n: int = 600, seed: int = 0, threshold: float = 52.0) -> dict:
    """Full analysis of a rendered video. spans: [{"id","beat","start","end"}] so weak points name the scene."""
    m = measure(path)
    sim = simulate(m, n=n, seed=seed)
    wp = weak_points(m, sim, spans)
    score = 100 * (0.40 * sim["avg_watch"] + 0.25 * sim["hold3"] + 0.15 * min(1.0, sim["finish"] * 3) + 0.20 * sim["sound_off_hold"])
    score -= sum(w["severity"] for w in wp[:4]) * 4
    score = float(np.clip(score, 0, 100))
    high = [w for w in wp if w["severity"] >= 0.5]
    return {"score": round(score, 1), "worth_posting": bool(score >= threshold and not [w for w in high if w["kind"] == "hook_leaks"]), "threshold": threshold,
            "duration": round(m["meta"]["duration"], 1), "avg_watch": round(sim["avg_watch"], 2), "hold3": round(sim["hold3"], 2), "finish": round(sim["finish"], 2),
            "sound_off_hold": round(sim["sound_off_hold"], 2), "curve": [round(c, 3) for c in sim["curve"]], "bots": sim["bots"], "weak_points": wp,
            "cuts": len(m["cut_times"]), "note": "heuristic bots over measured motion/cuts/text/voice; ranks and explains, does not forecast real views"}


def feedback(res: dict, planner_only: bool = True, limit: int = 8) -> str:
    """The detailed brief for a video planner: what the bots saw, the ranked weak points with times, scenes and fixes."""
    wp = [w for w in res["weak_points"] if w["planner"] or not planner_only][:limit]
    lines = [f"RETENTION REPORT from {sum(b['n'] for b in res['bots'].values())} simulated viewers (score {res['score']}/100, need {res['threshold']:.0f}): "
             f"{res['hold3']:.0%} still watching at 3s, average {res['avg_watch']:.0%} of the reel watched, {res['finish']:.0%} reach the end, muted viewers watch {res['sound_off_hold']:.0%}."]
    lines += [f"- {k}: {b['verdict']} (median leaves at {b['median_leaves_at']}s) - {b['about']}" for k, b in res["bots"].items() if b["verdict"] != "stays"]
    for i, w in enumerate(wp, 1):
        lines.append(f"{i}. [{w['kind']}] at {w['t']}s" + (f", scene {w['scene']} ({w['beat']})" if w.get("scene") else "") + f": {w['detail']}. FIX: {w['fix']}.")
    return "\n".join(lines)
