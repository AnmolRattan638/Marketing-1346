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
from . import edits
from .hybrid import Editor, HybridError
from .manifest import available_sfx, build_manifest
from .plan import make_plan, sample_plan
from .render import render
from .fx_plan import plan_fx, resolve_transition
from .sfx_plan import emphasis_beats, plan_sfx
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

    hybrid_on = (cfg.get("hybrid") or {}).get("enabled", True)
    service, topic = edits.detect_service(topic, cfg)
    log(f"service for this reel: {service}")
    editor = Editor(cfg, offline, service) if hybrid_on else None
    plan = sample_plan() if offline else make_plan(topic, cfg, editor.library_summary() if editor else "")
    (out_dir / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"plan: '{plan['title']}' with {len(plan['scenes'])} scenes")

    sfx_ok, used_ids, built, credits = available_sfx(), set(), [], []
    voiced = []
    for i, sc in enumerate(plan["scenes"]):
        sid = f"s{i + 1}"
        mp3 = WORK / "narration" / f"{sid}.mp3"
        seconds = synth(sc["narration"], mp3, cfg, offline)
        voiced.append((sid, sc, seconds, mp3, get_words(sc["narration"], mp3, seconds, cfg, offline)))
    if editor:   # the whole reel is planned at once so the hybrid rules apply to the reel, not to each scene
        editor.prepare([(sid, sc, sec + cfg["video"]["tail_seconds"]) for sid, sc, sec, _, _ in voiced], WORK / "footage",
                       {sid: words for sid, _, _, _, words in voiced})      # cuts are snapped to the spoken words
    for i, (sid, sc, seconds, mp3, words) in enumerate(voiced):
        if editor:
            clip = editor.render_scene(sid, WORK / "footage")
        else:
            clip = fetch_clip(sc, sid, WORK / "footage", used_ids, offline)
        fx = plan_fx(sc, words, seconds + cfg["video"]["tail_seconds"], cfg)      # graphics anchored to spoken words
        built.append({
            "id": sid, "clip": clip, "narration": f"assets/run/narration/{sid}.mp3",
            "narration_seconds": seconds, "words": words,
            "sfx": plan_sfx(i, sc, words, sfx_ok, clip.get("cuts"), fx),  # whooshes and clicks land on the real shot cuts; every graphic gets its sound
            "fx": fx, "transition": resolve_transition(sc, i, cfg),
            "beats": emphasis_beats(sc, words),                           # the same words drive caption emphasis and the zoom pulse
        })
        credits.append(clip["credit"])

    manifest = build_manifest(plan, built, cfg)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out_dir / "credits.json").write_text(json.dumps(credits, indent=2), encoding="utf-8")
    summary = ""
    if editor:
        shots = [x for b in built for x in b["clip"].get("shots", [])]
        total = sum(x["seconds"] for x in shots) or 1
        share = {t: sum(x["seconds"] for x in shots if x["type"] == t) / total for t in ("raw", "stock", "photo")}
        summary = (f"\nService: {service}. Hybrid: {len(shots)} shots, your raw {share['raw']:.0%}, stock {share['stock']:.0%}, photos {share['photo']:.0%}; "
                   f"cut rhythm {editor.prof['shot_min']}-{editor.prof['shot_max']}s from {editor.prof['reels_measured']} hero reel(s). {'All rules passed.' if not editor.violations else 'RULES NOT MET: ' + '; '.join(editor.violations)}")
        log(summary.strip())
    if no_render:
        log("--no-render: manifest written, stopping before Remotion")
        return

    final = out_dir / "final.mp4"
    render(manifest, final)
    log(f"done: {final} ({media_duration(final):.1f}s, {final.stat().st_size / 1e6:.1f} MB)")
    notify.send_video(final, f"{plan['title']}\nTopic: {topic}{summary}")


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
    except HybridError as e:
        print(e)
        try:
            notify.send_message(f"No reel today: {e}")
        except Exception:
            pass
        raise SystemExit(1)
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
