---
name: davinci-resolve
description: Editing inside DaVinci Resolve (free or Studio) - project and timeline setup, Cut/Edit/Fusion/Color/Fairlight/Deliver pages, color-managed workflows (DaVinci Wide Gamut, Color Space Transform for Apple Log/S-Log), node grading, Magic Mask, Speed Warp and optical flow, Smart Reframe, Voice Isolation, auto subtitles, Fusion titles, render presets for social, and automation via the Resolve scripting API (Python) or a DaVinci Resolve MCP server. Use when the project lives in Resolve or the user wants the edit delivered as a Resolve timeline.
---

# DaVinci Resolve

## 1. Project setup

- Timeline resolution: 1080x1920 or 2160x3840 for vertical (Project Settings → Master Settings → Custom, or "Use vertical resolution"). Set **timeline frame rate before importing** — it cannot change after the first timeline exists in free versions.
- Color management: Color Science **DaVinci YRGB Color Managed**, preset **SDR** (Rec.709 Gamma 2.4) for social, or **DaVinci Wide Gamut Intermediate** for mixed log sources. Or keep YRGB unmanaged and use a CST node per clip.
- Optimized media / proxies for 4K HEVC or ProRes RAW on slower machines.

## 2. Page by job

| Page | Use |
|---|---|
| Cut | fast assembly, source tape, sync bin, scene detect |
| Edit | precise trimming, J/L cuts (unlink audio, Alt-drag), titles, transitions, retime curves |
| Fusion | node compositing, tracking, particle/3D titles, keying (Delta Keyer), planar tracker |
| Color | primaries, curves, qualifiers, Power Windows + tracker, Magic Mask (Studio), LUTs, grain, Color Groups |
| Fairlight | dialogue cleanup (Voice Isolation Studio), EQ/dynamics, ducking, loudness meter (target -14 LUFS for social) |
| Deliver | render presets (YouTube, Vimeo, custom H.264/H.265), render queue |

## 3. Techniques that matter

- **Speed ramps**: Retime Controls (Ctrl+R) → speed points, then Retime Curve with eased handles; Retime Process **Optical Flow**, Motion Estimation **Speed Warp** (Studio) for slow motion from 24-30 fps.
- **Smart Reframe** (Studio): 16:9 → 9:16 with auto subject tracking; check and keyframe.
- **Auto subtitles** (Studio 18.5+): Timeline → Create Subtitles from Audio; style in the subtitle track inspector.
- **Magic Mask** (Studio): person/feature masks for subject-only grades or background blur.
- **Node baseline**: `CST in → Balance → Contrast/Sat → Skin qualifier → Look → CST out → Grain`.
- **Day for Night**: Resolve ships an "LMT Day for Night" (ACES) — apply it in an ACES project, or bake it into a Rec.709 LUT for ffmpeg (see `color-grading`).
- **Apple Log**: CST input Apple Log / Rec.2020, output Rec.709 Gamma 2.4, tone mapping on.
- **Fusion text on a surface**: Planar Tracker (track) → Corner Pin the Text+ → Merge.
- **Beat markers**: play the song and press M on beats in the Edit page; snap cuts to markers.

## 4. Social render preset (Deliver → Custom)

H.264 (or H.265 for 4K), resolution matching timeline (2160x3840 or 1080x1920), frame rate = timeline, quality restrict to 40-60 Mbps for 4K / 20-25 Mbps for 1080p, AAC 320 kbps, "Force sizing to highest quality" and "Force debayer to highest quality" on. Tag Rec.709 Gamma 2.4 (for web, some prefer Rec.709-A on Mac to avoid gamma shift in QuickTime).

## 5. Automation

- **Resolve scripting API** (Python/Lua; Studio for external scripting, free version from the in-app console): `import DaVinciResolveScript as dvr; resolve = dvr.scriptapp("Resolve")`. Env vars on Windows: `RESOLVE_SCRIPT_API=%PROGRAMDATA%\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting`, `RESOLVE_SCRIPT_LIB=C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll`, add `%RESOLVE_SCRIPT_API%\Modules` to `PYTHONPATH`.
- Typical script: create project → import media → `MediaPool.CreateTimelineFromClips` or `AppendToTimeline([{mediaPoolItem, startFrame, endFrame}])` from your EDL → apply LUT/CDL (`TimelineItem.SetLUT`, `SetCDL`) → add render job → render.
- **MCP server**: if `mcp__davinci-resolve__*` tools are present (community "davinci-resolve-mcp" servers), load them with ToolSearch and use them for timelines, markers, grading, Fusion and renders instead of writing raw API code.
- Hybrid workflow that works well: analyse and plan in Python (beats, transcript, EDL), build the timeline in Resolve via API/MCP, grade and finish in Resolve, or render everything in ffmpeg and use Resolve only for the grade.

## 6. Gotchas

- Free version: no external scripting, no Magic Mask/Speed Warp/Voice Isolation/Smart Reframe, max UHD 60p export.
- Vertical HEVC from iPhones can import with rotation — check the clip's Inspector rotation.
- HDR (HLG) iPhone clips in an SDR timeline: set input color space correctly or enable tone mapping, otherwise they look washed out.
- Timeline frame-rate mismatches (29.97 vs 30) cause drift against music; match the source.
