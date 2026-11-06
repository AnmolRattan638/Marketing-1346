"""Entry point: python -m agent.run [--topic "..."] [--offline] [--no-render]"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import traceback
from datetime import date

from . import notify
from .captions import get_words
from .common import ROOT, WORK, load_config, log, media_duration
from .footage import fetch_clip
from .manifest import available_sfx, build_manifest
from .plan import make_plan, sample_plan
from .render import render
from .sfx_plan import plan_sfx
from .voice import synth


def pick_topic(arg_topic: str | None) -> str:
    if arg_topic:
        return arg_topic
    if os.environ.get("TOPIC"):
        return os.environ["TOPIC"]
    lines = [l.strip() for l in (ROOT / "topics.txt").read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    if not lines:
        raise SystemExit("topics.txt has no topics. Add some or pass --topic.")
    return lines[date.today().toordinal() % len(lines)]


def build(topic: str, offline: bool, no_render: bool) -> None:
    cfg = load_config()
    out_dir = ROOT / "runs" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(WORK, ignore_errors=True)
    (WORK / "footage").mkdir(parents=True)
    (WORK / "narration").mkdir(parents=True)

    plan = sample_plan() if offline else make_plan(topic, cfg)
    (out_dir / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"plan: '{plan['title']}' with {len(plan['scenes'])} scenes")

    sfx_ok, used_ids, built, credits = available_sfx(), set(), [], []
    for i, sc in enumerate(plan["scenes"]):
        sid = f"s{i + 1}"
        clip = fetch_clip(sc, sid, WORK / "footage", used_ids, offline)
        mp3 = WORK / "narration" / f"{sid}.mp3"
        seconds = synth(sc["narration"], mp3, cfg, offline)
        words = get_words(sc["narration"], mp3, seconds, cfg, offline)
        built.append({
            "id": sid, "clip": clip, "narration": f"assets/run/narration/{sid}.mp3",
            "narration_seconds": seconds, "words": words,
            "sfx": plan_sfx(i, sc, words, sfx_ok),
        })
        credits.append(clip["credit"])

    manifest = build_manifest(plan, built, cfg)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out_dir / "credits.json").write_text(json.dumps(credits, indent=2), encoding="utf-8")
    if no_render:
        log("--no-render: manifest written, stopping before Remotion")
        return

    final = out_dir / "final.mp4"
    render(manifest, final)
    log(f"done: {final} ({media_duration(final):.1f}s, {final.stat().st_size / 1e6:.1f} MB)")
    notify.send_video(final, f"{plan['title']}\nTopic: {topic}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic")
    ap.add_argument("--offline", action="store_true",
                    help="no network: sample plan, placeholder footage, silent voice (for testing)")
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()
    topic = pick_topic(args.topic) if not args.offline else "offline sample"
    try:
        build(topic, args.offline, args.no_render)
    except Exception:
        err = traceback.format_exc()
        print(err)
        try:
            notify.send_message("Video run failed:\n" + err[-1500:])
        except Exception:
            pass
        raise SystemExit(1)


if __name__ == "__main__":
    main()
