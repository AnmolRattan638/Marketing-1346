"""Regenerate knowledge/INDEX.md: every skill document, its one-line description and what the pipeline does with it.   python tools/build_knowledge_index.py"""
from __future__ import annotations

import re
from pathlib import Path

K = Path(__file__).resolve().parent.parent / "knowledge"
HARD = "IN CODE"
TEXT = "IN THE PLANNER PROMPT"
REF = "reference only"
STATUS = {
    "sound-design": (HARD, "SFX placement on the frame, levels under speech and the -14 LUFS target are code: agent/sfxkit.py, agent/sfx_plan.py, agent/finish.py"),
    "style-instagram-reels": (TEXT, "hook on frame 0, a change every 3 s, loop ending, safe area: distilled into skills/sfx-notes.md (the template already keeps graphics below the logo-safe top, LOGO_SAFE_TOP)"),
    "editing-foundations": (REF, "cut-type vocabulary; the planner's own rules already cover hook, pace and payoff"),
    "captions-typography": (REF, "the pipeline has its own caption system (agent/captions.py, agent/caption_zones.py, template/src)"),
    "beat-sync": (REF, "reels here are voice-led, not music-cut"),
    "color-grading": (REF, "the look system (agent/looks.py) already grades"),
    "ffmpeg-pipeline": (REF, "Remotion renders; ffmpeg is used only for probing, clips and the loudness step"),
    "motion-tracking": (REF, "no tracked footage in the pipeline"),
    "reel-hand-text": (REF, "a different text style"),
    "reference-matching": (REF, "recreating another reel's timing is not part of the pipeline"),
    "shoot-planning": (REF, "pre-production for real shoots"),
    "video-editing": (REF, "router skill for interactive editing sessions"),
    "davinci-resolve": (REF, "another editor"),
}
UV = {
    "sound-design/sfx-guide.md": (HARD, "SFX vocabulary and layering: agent/sfxkit.py, agent/sfx_plan.py"),
    "sound-design/audio-mixing.md": (HARD, "mix levels and loudness: agent/finish.py and the kit's under-voice levels"),
    "social-media/viral-editing.md": (TEXT, "retention rules: distilled into skills/sfx-notes.md"),
    "social-media/platform-specs.md": (HARD, "loudness and delivery targets: agent/finish.py"),
}


def desc(md: Path) -> str:
    m = re.search(r"^description:\s*(.+)$", md.read_text(encoding="utf-8"), re.M)
    return (m.group(1).strip() if m else "")[:150]


def main() -> None:
    rows = ["# Knowledge base", "",
            "Reference copies of three open-source packs (licences next to each). They are NOT loaded into the planner: it reads only three skill files "
            "(`skills/`, capped for the free-tier token limits). What the pipeline actually uses is in code or in `skills/sfx-notes.md`, as marked below.",
            "", "| Pack | Skill | What it covers | Used for |", "|---|---|---|---|"]
    for d in sorted((K / "video-editing-skills" / "skills").iterdir()):
        s = STATUS.get(d.name, (REF, ""))
        rows.append(f"| video-editing-skills (MIT) | `{d.name}` | {desc(d / 'SKILL.md')} | **{s[0]}**{': ' + s[1] if s[1] else ''} |")
    base = K / "ultimate-video-editor" / "ultimate-video-editor"
    rows.append(f"| Ultimate-Video-Editing-Skills (MIT) | `ultimate-video-editor/SKILL.md` | {desc(base / 'SKILL.md')} | {REF}: the master skill |")
    for f in sorted(base.rglob("*.md")):
        rel = f.relative_to(base).as_posix()
        if rel == "SKILL.md":
            continue
        s = UV.get(rel, (REF, ""))
        rows.append(f"| Ultimate-Video-Editing-Skills (MIT) | `{rel}` | | **{s[0]}**{': ' + s[1] if s[1] else ''} |")
    rows += ["| SFX Kit (CC0) | `sfx-kit/GUIDE.md`, `catalogue.md` | how to find, place and level its 320 sounds | **IN CODE**: the 320 sounds are `assets/sfxkit/` (MP3, levels unchanged) with `catalog.json`; `tools/import_sfx_kit.py` rebuilds them |",
             "", "Helper scripts shipped inside the skill packs (beat detection, grading, tracking, mixing) are not copied: the pipeline does not run third-party scripts.", ""]
    (K / "INDEX.md").write_text("\n".join(rows), encoding="utf-8")
    print(f"INDEX.md: {len(rows)} lines")


if __name__ == "__main__":
    main()
