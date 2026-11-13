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
from . import footage as _footage
from .footage import fetch_clip
from . import edits, master_script, webresearch
from .hybrid import Editor, HybridError
from .manifest import available_sfx, build_manifest
from .plan import make_plan, sample_plan
from .render import render
from .fx_plan import plan_fx
from .camera_plan import plan_camera
from .caption_zones import zones_for
from .brand import load_palette
from .looks import pick_look, pick_transition
from .graphics import fallback_graphic, resolve_graphic
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


def build(topic: str, offline: bool, no_render: bool, master: dict | None = None) -> None:
    cfg = load_config()
    _footage._CFG = cfg          # stock.keywords / stock.anchors keep stock strictly about AI and technology
    out_dir = ROOT / "runs" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(WORK, ignore_errors=True)
    (WORK / "footage").mkdir(parents=True)
    (WORK / "narration").mkdir(parents=True)

    hybrid_on = (cfg.get("hybrid") or {}).get("enabled", True)
    service, topic = edits.detect_service(topic, cfg)
    if master and master.get("service"):
        service = master["service"]
    log(f"service for this reel: {service}")
    editor = Editor(cfg, offline, service) if hybrid_on else None
    look = pick_look(f"{date.today().isoformat()}|{topic}", cfg) if not offline else {"caption": "cinematic", "transitions": "mixed", "palette": load_palette(cfg)}
    # with a master script the research is already done and fact-checked (its fact sheet), so the video does no research of its own
    ev_text, sources = ("", []) if (offline or master) else webresearch.for_topic(topic)       # real sources for the topic (Tavily + Exa), optional
    if master:
        sources = [{"title": f.get("claim", "")[:80], "url": f.get("url"), "domain": f.get("source")} for f in master.get("facts", []) if f.get("url")]
    plan = sample_plan() if offline else make_plan(topic, cfg, editor.library_summary() if editor else "", service, **({"evidence": ev_text} if ev_text else {}), **({"master": master} if master else {}))
    if sources:
        plan["sources"] = sources
    (out_dir / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"plan: '{plan['title']}' with {len(plan['scenes'])} scenes")

    sfx_ok, used_ids, built, credits = available_sfx(), set(), [], []
    voiced = []
    for i, sc in enumerate(plan["scenes"]):
        sid = f"s{i + 1}"
        mp3 = WORK / "narration" / f"{sid}.mp3"
        seconds = synth(sc["narration"], mp3, cfg, offline)
        voiced.append((sid, sc, seconds, mp3, get_words(sc["narration"], mp3, seconds, cfg, offline)))
    tail = cfg["video"]["tail_seconds"]
    # Each scene is either a motion graphic (the default look) or footage (your own clips, at most max_stock_shots stock shots in the reel).
    graphics: dict[str, dict] = {}
    for sid, sc, sec, _, words in voiced:
        if sc.get("graphic") or (editor and not editor.avail["raw"]):
            if not sc.get("graphic"):
                log(f"{sid}: no raw clips to show, so this scene becomes a motion graphic instead of stock footage")
                sc["graphic"] = fallback_graphic(sc)
            gp = resolve_graphic(sc, words, sec + tail)
            if gp:
                graphics[sid] = gp
            else:
                sc.pop("graphic", None)
        sc.setdefault("footage_query", "ai automation technology")
    footage_scenes = [(sid, sc, sec + tail) for sid, sc, sec, _, _ in voiced if sid not in graphics]
    if editor and footage_scenes:   # the whole reel is planned at once so the hybrid rules apply to the reel, not to each scene
        editor.prepare(footage_scenes, WORK / "footage", {sid: words for sid, _, _, _, words in voiced})      # cuts are snapped to the spoken words
    for i, (sid, sc, seconds, mp3, words) in enumerate(voiced):
        transition = pick_transition(sc, i, look, cfg)
        gp = graphics.get(sid)
        if gp:
            clip, fx, zones, camera = None, plan_fx(sc, words, seconds + tail, cfg), [], []
            sfx = plan_sfx(i, sc, words, sfx_ok, None, fx, transition, gp["sfx"], cfg.get("sfx_policy"))
            credits.append({"scene": sid, "graphic": gp["layout"]})
        else:
            clip = editor.render_scene(sid, WORK / "footage") if editor else fetch_clip(sc, sid, WORK / "footage", used_ids, offline)
            fx = plan_fx(sc, words, seconds + tail, cfg)      # graphics anchored to spoken words
            camera = plan_camera(sc, words, seconds + tail, clip.get("shots"), i, cfg)
            zones = zones_for(WORK / "footage" / f"{sid}.mp4", seconds + tail) if (cfg.get("captions") or {}).get("smart_position", True) else []
            sfx = plan_sfx(i, sc, words, sfx_ok, clip.get("cuts"), fx, transition, None, cfg.get("sfx_policy"))
            credits.append(clip["credit"])
        built.append({
            "id": sid, "clip": clip, "graphic": gp, "narration": f"assets/run/narration/{sid}.mp3",
            "narration_seconds": seconds, "words": words, "sfx": sfx, "fx": fx, "transition": transition, "zones": zones, "camera": camera,
            "beats": emphasis_beats(sc, words),                           # the same words drive caption emphasis and the zoom pulse
        })

    manifest = build_manifest(plan, built, cfg, look)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out_dir / "credits.json").write_text(json.dumps(credits, indent=2), encoding="utf-8")
    summary = ""
    if editor:
        shots = [x for b in built if b["clip"] for x in b["clip"].get("shots", [])]
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
    notify.send_video(final, ("Reel for today's draft (same script as the carousel). Approving the draft posts the carousel; post this Reel yourself.\n" if master else "") + f"{plan['title']}\nTopic: {topic}{summary}{webresearch.caption_line(plan.get('sources') or [])}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic")
    ap.add_argument("--offline", action="store_true",
                    help="no network: sample plan, placeholder footage, silent voice (for testing)")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--script", help="master script JSON (default: today's draft in data/drafts); the video then follows it word for word")
    ap.add_argument("--no-script", action="store_true", help="ignore any master script and plan from topics.txt")
    args = ap.parse_args()
    master = None if (args.offline or args.no_script or args.topic or os.environ.get("TOPIC")) else master_script.load(args.script)
    if master:
        log(f"master script found: style {master.get('style')}, topic '{master.get('topic')}'")
    topic = (master or {}).get("topic") or (pick_topic(args.topic) if not args.offline else "offline sample")
    try:
        build(topic, args.offline, args.no_render, master)
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
