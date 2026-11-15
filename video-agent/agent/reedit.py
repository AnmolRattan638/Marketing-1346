"""Re-edit a finished clip: you give the clip and say in plain words what to change; the agent edits it.

    python -m agent.reedit --video <Drive link | URL | file> --instructions "at 12 s explain the 3-step procedure, zoom in on the phone number..."

What it can do (the planner chooses from exactly these, from your words and from what is said in the clip):
  procedure   a step-by-step motion graphic whose steps light up on the spoken words
  title / stat / lower_third / glitch   the same animated text effects the daily reels use
  zoom        a push-in on the picture for a few seconds
  cut         remove a part (everything after it is re-timed)
The original picture, its captions, logo and audio are kept as they are: this adds to the clip, it does not rebuild it. Output goes to Telegram and to runs/reedit-*/.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import time
from pathlib import Path

import requests

from . import captions, notify, plan as planner
from .common import ROOT, TEMPLATE, load_config, log, media_duration, run

FX_TYPES = ("stat", "glitch", "title", "lower_third")
POSITIONS = ("top", "middle", "bottom")
LIMITS = {"title": 28, "step": 36, "fx_text": 40, "steps": (2, 5), "zoom": (1.1, 1.6), "max_cut_share": 0.4, "min_gap": 0.4}


# ---------------------------------------------------------------- input
def fetch(src: str, dest: Path) -> Path:
    """The clip from a local path, a Google Drive share link or a direct URL."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.startswith("telegram:"):
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set, so the video cannot be fetched from Telegram")
        info = requests.get(f"https://api.telegram.org/bot{token}/getFile", params={"file_id": src[9:]}, timeout=60).json()
        if not info.get("ok"):
            raise RuntimeError("Telegram would not give me that video (" + str(info.get("description"))[:120] + "). Telegram bots can only download files up to 20 MB: send a shorter copy or a Drive link")
        with requests.get(f"https://api.telegram.org/file/bot{token}/{info['result']['file_path']}", stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
    elif Path(src).exists():
        shutil.copy(src, dest)
    elif "drive.google.com" in src or "docs.google.com" in src:
        import gdown
        got = gdown.download(url=src, output=str(dest), quiet=True, fuzzy=True)
        if not got:
            raise RuntimeError("could not download the clip from Google Drive: share the file as 'Anyone with the link' and paste the link again")
    elif src.startswith("http"):
        with requests.get(src, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
    else:
        raise RuntimeError(f"cannot find the clip: {src!r} is not a file, a Drive link or a URL")
    if not dest.exists() or dest.stat().st_size < 10_000:
        raise RuntimeError("the downloaded clip is empty or not a video (a Drive link that needs sign-in downloads as a web page)")
    return dest


HINGLISH_PROMPT = "यह हिंदी और अंग्रेज़ी मिली हुई वॉयसओवर है: क्या आपको लगता है कि आपके सारे कस्टमर्स गूगल से मिल जाएंगे? वेबसाइट, चैटबॉट, WhatsApp, बिज़नेस।"
WINDOW = 4.0                 # seconds; a spoken window with fewer than MIN_WORDS words while it is clearly audible is transcribed again on its own
MIN_WORDS = 4
AUDIBLE_DB = -38.0


def window_db(wav: Path, a: float, b: float) -> float:
    """Mean volume (dB) of a time window; -91 when it cannot be measured."""
    p = run(["ffmpeg", "-hide_banner", "-ss", f"{a:.2f}", "-t", f"{b - a:.2f}", "-i", wav, "-af", "volumedetect", "-vn", "-f", "null", "-"], capture=True)
    m = re.search(r"mean_volume: (-?[\d.]+) dB", (p.stderr or "") + (p.stdout or ""))
    return float(m.group(1)) if m else -91.0


def fill_gaps(words: list[dict], duration: float, loud, again) -> list[dict]:
    """Whisper often drops the first seconds of a clip (the hook) or a stretch under music. Every WINDOW-second stretch that is audible but has too few words is
    transcribed again on its own (loud(a, b) -> dB, again(a, b) -> words with times in the whole clip); the result replaces the sparse words only if it found more."""
    out = list(words)
    t = 0.0
    while t < duration - 0.8:
        a, b = t, min(duration, t + WINDOW)
        have = [w for w in out if a <= w["start"] < b]
        if len(have) < MIN_WORDS and loud(a, b) > AUDIBLE_DB:
            new = [w for w in again(max(0, a - 0.3), min(duration, b + 0.3)) if a - 0.05 <= w["start"] < b]
            if len(new) > len(have):
                out = [w for w in out if not (a <= w["start"] < b)] + new
        t += WINDOW
    return sorted(out, key=lambda w: w["start"])


def transcript(video: Path, cfg: dict) -> list[dict]:
    """Word timings of what is said in the clip (empty when speech-to-text is unavailable: the plan then relies on the instructions alone)."""
    wav = video.with_suffix(".speech.wav")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-af", "highpass=f=90,loudnorm=I=-18:TP=-2", wav])
    lang = cfg.get("voice_language", "hi")
    c = {**cfg, "captions": {"model": "whisper-large-v3-turbo", **cfg.get("captions", {})}}

    def hear(path: Path, offset: float = 0.0) -> list[dict]:
        mp3 = path.with_suffix(".mp3")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-b:a", "64k", mp3])
        last = None
        for model in ("whisper-large-v3", c["captions"]["model"]):         # the bigger model first: it keeps the quiet / fast words
            try:
                ws = captions._transcribe(mp3, lang, c, prompt=HINGLISH_PROMPT, model=model)
                return [{**w, "start": w["start"] + offset, "end": w["end"] + offset} for w in ws]
            except Exception as e:
                last = e
        raise last

    try:
        words = hear(wav)
    except Exception as e:
        log(f"transcription failed ({str(e)[:120]}); planning from the instructions only")
        return []
    duration = media_duration(video)

    def again(a: float, b: float) -> list[dict]:
        part = video.with_suffix(f".w{int(a * 10)}.wav")
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.2f}", "-t", f"{b - a:.2f}", "-i", wav, part])
        try:
            return hear(part, a)
        except Exception:
            return []

    try:
        words = fill_gaps(words, duration, lambda a, b: window_db(wav, a, b), again)
    except Exception as e:
        log(f"gap check skipped ({str(e)[:100]})")
    return words


def lines(words: list[dict]) -> str:
    """The transcript as timed phrases, for the planner."""
    out, cur = [], []
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > 0.5 or len(cur) >= 7):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return "\n".join(f"[{c[0]['start']:.1f}-{c[-1]['end']:.1f}] " + " ".join(x["text"] for x in c) for c in out)


# ---------------------------------------------------------------- plan
SYSTEM = (
    "You are the editor of a short vertical video. The user's finished clip already has its own picture, captions, logo and audio. You ADD motion graphics and simple edits to it, "
    "exactly as the user asks, using only the operations below. Times are seconds in the ORIGINAL clip. Return one JSON object, nothing else:\n"
    '{"summary": "one plain sentence on what you will do",\n'
    ' "cuts": [{"from": s, "to": s}],\n'
    ' "zooms": [{"from": s, "to": s, "scale": 1.1-1.6, "x": 0-1, "y": 0-1}],\n'
    ' "procedures": [{"from": s, "to": s, "title": "<=28 chars", "position": "top|middle|bottom", "steps": [{"text": "<=36 chars", "at": s}]}],\n'
    ' "fx": [{"type": "title|stat|lower_third|glitch", "at": s, "seconds": s, "text": "<=40 chars", "label": "short", "value": number, "prefix": "", "suffix": ""}]}\n'
    "RULES: do ONLY what the user asked; leave a list empty when not asked. A procedure has 2-5 steps; each step's `at` is the moment its words are SPOKEN in the transcript "
    "(use the transcript times) or, when nothing is said about it, evenly spread across from..to. `from` is just before the first step, `to` is about 1.5 s after the last step starts. "
    "Step text is the action in a few words, in the language the clip speaks (Hinglish in Roman letters is fine). Put a procedure at the top unless the user says otherwise (the logo is top-left "
    "and is never covered; captions move around the lower and middle area). Two graphics must not be on screen at the same time. A `stat` needs a numeric `value` that the user gave or the clip states. "
    "Never invent facts, names or numbers. Keep every time inside the clip's length."
)


def problems(ops: dict, seconds: float) -> list[str]:
    """What is wrong with a plan, as concrete mistakes (which item, what it wrote, what is allowed)."""
    out: list[str] = []
    if not isinstance(ops, dict):
        return ["the answer is not a JSON object"]
    cuts, zooms, procs, fx = (ops.get(k) or [] for k in ("cuts", "zooms", "procedures", "fx"))
    for i, c in enumerate(cuts, 1):
        if not (isinstance(c, dict) and 0 <= c.get("from", -1) < c.get("to", -1) <= seconds + 0.01):
            out.append(f"cut {i}: needs 0 <= from < to <= {seconds:.1f} (got {c})")
    if sum(max(0, c.get("to", 0) - c.get("from", 0)) for c in cuts if isinstance(c, dict)) > LIMITS["max_cut_share"] * seconds:
        out.append(f"cuts remove more than {int(LIMITS['max_cut_share'] * 100)}% of the clip; cut less")
    for i, z in enumerate(zooms, 1):
        if not (isinstance(z, dict) and 0 <= z.get("from", -1) < z.get("to", -1) <= seconds + 0.01 and LIMITS["zoom"][0] <= z.get("scale", 0) <= LIMITS["zoom"][1]):
            out.append(f"zoom {i}: needs 0 <= from < to <= {seconds:.1f} and scale between {LIMITS['zoom'][0]} and {LIMITS['zoom'][1]} (got {z})")
    spans = []
    for i, p in enumerate(procs, 1):
        if not isinstance(p, dict):
            out.append(f"procedure {i} is not an object")
            continue
        st = p.get("steps") or []
        if not LIMITS["steps"][0] <= len(st) <= LIMITS["steps"][1]:
            out.append(f"procedure {i}: has {len(st)} steps; it needs {LIMITS['steps'][0]} to {LIMITS['steps'][1]}")
        if not (0 <= p.get("from", -1) < p.get("to", -1) <= seconds + 0.01):
            out.append(f"procedure {i}: from/to must satisfy 0 <= from < to <= {seconds:.1f} (got {p.get('from')}..{p.get('to')})")
        if p.get("position", "top") not in POSITIONS:
            out.append(f"procedure {i}: position \"{p.get('position')}\" does not exist; use top, middle or bottom")
        if len(str(p.get("title") or "")) > LIMITS["title"]:
            out.append(f"procedure {i}: title is {len(str(p['title']))} characters, the limit is {LIMITS['title']}")
        for j, s in enumerate(st, 1):
            if not isinstance(s, dict) or not str(s.get("text") or "").strip():
                out.append(f"procedure {i} step {j}: needs text")
            elif len(s["text"]) > LIMITS["step"]:
                out.append(f"procedure {i} step {j}: \"{s['text']}\" is {len(s['text'])} characters, the limit is {LIMITS['step']}")
            elif not (p.get("from", 0) - 0.01 <= s.get("at", -1) <= p.get("to", 0)):
                out.append(f"procedure {i} step {j}: `at` {s.get('at')} must lie between the procedure's from and to ({p.get('from')}..{p.get('to')})")
        spans.append((p.get("from", 0), p.get("to", 0), f"procedure {i}"))
    for i, f in enumerate(fx, 1):
        if not isinstance(f, dict) or f.get("type") not in FX_TYPES:
            out.append(f"fx {i}: type \"{(f or {}).get('type') if isinstance(f, dict) else f}\" does not exist; allowed: {', '.join(FX_TYPES)}")
            continue
        if not (0 <= f.get("at", -1) < seconds and 0.5 <= f.get("seconds", 0) <= 8):
            out.append(f"fx {i}: needs 0 <= at < {seconds:.1f} and seconds between 0.5 and 8")
        if f["type"] == "stat" and not isinstance(f.get("value"), (int, float)):
            out.append(f"fx {i}: a stat needs a numeric `value`")
        if f["type"] != "stat" and not str(f.get("text") or "").strip():
            out.append(f"fx {i}: {f['type']} needs `text`")
        if len(str(f.get("text") or "")) > LIMITS["fx_text"]:
            out.append(f"fx {i}: text is {len(f['text'])} characters, the limit is {LIMITS['fx_text']}")
        spans.append((f.get("at", 0), f.get("at", 0) + f.get("seconds", 0), f"fx {i}"))
    spans.sort()
    for a, b in zip(spans, spans[1:]):
        if b[0] < a[1] - 0.05:
            out.append(f"{a[2]} ({a[0]:.1f}-{a[1]:.1f}s) and {b[2]} ({b[0]:.1f}-{b[1]:.1f}s) are on screen together; move one so they do not overlap")
    return out


def make_plan(instructions: str, words: list[dict], seconds: float, cfg: dict, ask=None) -> dict:
    ask = ask or planner._call_groq
    user = (f"CLIP LENGTH: {seconds:.1f} s\nTRANSCRIPT (timed):\n{lines(words) or '(speech-to-text unavailable: spread things evenly and follow the instructions)'}\n\n"
            f"WHAT THE USER WANTS (follow it, do nothing else):\n{instructions.strip()}\n\nReturn the JSON.")
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    bad: list[str] = []
    for attempt in (1, 2, 3):
        raw = ask(messages, cfg)
        try:
            ops = json.loads(raw)
            bad = problems(ops, seconds)
        except json.JSONDecodeError as e:
            ops, bad = None, [f"not valid JSON: {e}"]
        if not bad:
            return ops
        log(f"edit plan attempt {attempt} rejected: " + " | ".join(bad[:5]))
        messages += [{"role": "assistant", "content": raw},
                     {"role": "user", "content": "Rejected for these concrete mistakes. Fix every one and return the full JSON again:\n- " + "\n- ".join(bad[:8])}]
    raise RuntimeError("the edit plan was rejected 3 times: " + " | ".join(bad[:4]))


# ---------------------------------------------------------------- apply
def kept_segments(cuts: list[dict], seconds: float) -> list[tuple[float, float]]:
    cs = sorted((max(0, c["from"]), min(seconds, c["to"])) for c in cuts)
    out, pos = [], 0.0
    for a, b in cs:
        if a - pos > 0.05:
            out.append((pos, a))
        pos = max(pos, b)
    if seconds - pos > 0.05:
        out.append((pos, seconds))
    return out or [(0.0, seconds)]


def remap(t: float, segs: list[tuple[float, float]]) -> float | None:
    """Time in the cut clip of original time t; None when t falls inside a cut."""
    acc = 0.0
    for a, b in segs:
        if a <= t <= b:
            return acc + (t - a)
        acc += b - a
    return None


def snap(t: float, words: list[dict], reach: float = 0.35) -> float:
    """Move a start time onto the nearest spoken word start when one is close, so a step lights up as its word begins."""
    best = min(words, key=lambda w: abs(w["start"] - t), default=None)
    return best["start"] if best and abs(best["start"] - t) <= reach else t


def build_props(ops: dict, words: list[dict], segs: list[tuple[float, float]], seconds: float) -> dict:
    total = sum(b - a for a, b in segs)
    R = lambda t: remap(t, segs)
    props: dict = {"video": "reedit/base.mp4", "seconds": round(total, 3), "zooms": [], "procedures": [], "fx": []}
    for z in ops.get("zooms") or []:
        a, b = R(z["from"]), R(min(z["to"], seconds))
        if a is not None and b is not None and b - a > 0.6:
            props["zooms"].append({"from": a, "to": b, "scale": z["scale"], "x": min(1, max(0, z.get("x", 0.5))), "y": min(1, max(0, z.get("y", 0.5)))})
    for p in ops.get("procedures") or []:
        steps = [(snap(s["at"], words), s["text"]) for s in sorted(p["steps"], key=lambda s: s["at"])]
        mapped = [(R(t), x) for t, x in steps]
        if any(t is None for t, _ in mapped):
            log("a procedure step falls inside a cut; that procedure is skipped")
            continue
        start = max(0.0, R(max(p["from"], 0)) if R(p["from"]) is not None else mapped[0][0] - 0.3)
        end = min(total, max(R(p["to"]) or 0, mapped[-1][0] + 1.5))
        props["procedures"].append({"type": "procedure", "from": min(start, mapped[0][0] - 0.2), "to": end, "title": p.get("title") or "", "position": p.get("position", "top"),
                                    "steps": [{"text": x, "at": t} for t, x in mapped]})
    for f in ops.get("fx") or []:
        a = R(snap(f["at"], words))
        if a is None:
            continue
        item = {"type": f["type"], "atSecond": a, "seconds": min(f["seconds"], max(0.5, total - a)), "text": f.get("text"), "label": f.get("label")}
        if f["type"] == "stat":
            item.update(value=f["value"], prefix=f.get("prefix", ""), suffix=f.get("suffix", ""))
        props["fx"].append(item)
    return props


def cut_video(src: Path, dest: Path, segs: list[tuple[float, float]], seconds: float) -> None:
    if len(segs) == 1 and segs[0] == (0.0, seconds):
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-r", "30", "-c:a", "aac", "-b:a", "160k", dest])
        return
    parts, ins = [], ""
    for i, (a, b) in enumerate(segs):
        parts.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS,fps=30[v{i}];[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[a{i}]")
        ins += f"[v{i}][a{i}]"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-filter_complex", ";".join(parts) + f";{ins}concat=n={len(segs)}:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", "-c:a", "aac", "-b:a", "160k", dest])


def render(props: dict, out: Path) -> None:
    pf = TEMPLATE / "reedit_props.json"
    pf.write_text(json.dumps(props), encoding="utf-8")
    cmd = ["npx", "remotion", "render", "src/index.ts", "ReEdit", out, "--props", str(pf), "--overwrite", "--codec", "h264", "--crf", "20"]
    if os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
        cmd += ["--browser-executable", os.environ["REMOTION_BROWSER_EXECUTABLE"]]
    run(cmd, cwd=TEMPLATE)


def describe(props: dict, ops: dict) -> str:
    bits = []
    if props["procedures"]:
        bits.append(f"{len(props['procedures'])} step graphic(s)")
    if props["fx"]:
        bits.append(f"{len(props['fx'])} text effect(s)")
    if props["zooms"]:
        bits.append(f"{len(props['zooms'])} zoom(s)")
    if ops.get("cuts"):
        bits.append(f"{len(ops['cuts'])} cut(s)")
    return (ops.get("summary") or "Re-edit done") + (" (" + ", ".join(bits) + ")" if bits else "")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=os.environ.get("INPUT_VIDEO", ""))
    ap.add_argument("--instructions", default=os.environ.get("INSTRUCTIONS", ""))
    ap.add_argument("--ops-file", help="skip the AI planner and use this plan (tests)")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args(argv)
    out_dir = ROOT / "runs" / time.strftime("reedit-%Y%m%d-%H%M%S")
    cfg = load_config()
    try:
        if not a.video or not (a.instructions.strip() or a.ops_file):
            raise RuntimeError("give the clip (--video) and what to change (--instructions)")
        src = fetch(a.video, out_dir / "original.mp4")
        seconds = media_duration(src)
        words = [] if a.ops_file else transcript(src, cfg)
        (out_dir / "transcript.txt").write_text(lines(words), encoding="utf-8")
        ops = json.loads(Path(a.ops_file).read_text()) if a.ops_file else make_plan(a.instructions, words, seconds, cfg)
        (out_dir / "edit_plan.json").write_text(json.dumps(ops, ensure_ascii=False, indent=1), encoding="utf-8")
        segs = kept_segments(ops.get("cuts") or [], seconds)
        base = TEMPLATE / "public" / "reedit" / "base.mp4"
        base.parent.mkdir(parents=True, exist_ok=True)
        cut_video(src, base, segs, seconds)
        props = build_props(ops, words, segs, seconds)
        (out_dir / "props.json").write_text(json.dumps(props, indent=1), encoding="utf-8")
        if a.no_render:
            return
        out = out_dir / "edited.mp4"
        render(props, out)
        notify.send_video(out, "Re-edit: " + describe(props, ops))
        if words:
            notify.send_message("What I heard in your clip (check the planned timings against this):\n" + lines(words))
        log(f"done: {out}")
    except Exception as e:
        log(f"re-edit failed: {e}")
        try:
            notify.send_message(f"Re-edit failed: {str(e)[:900]}")
        except Exception:
            pass
        raise SystemExit(1)


if __name__ == "__main__":
    main()
