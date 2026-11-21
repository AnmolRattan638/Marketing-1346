---
name: shoot-planning
description: Pre-production for videos that will be edited - concept and hook, script, shot list, storyboard, B-roll lists, and camera settings for phones and cameras (resolution, frame rate, 180-degree shutter, flicker-free shutter for 50/60 Hz mains, ISO limits, white balance lock, log profiles like Apple Log, ProRes vs HEVC, stabilization, audio). Use when the user is about to shoot, asks what to film, or needs a storyboard or shot list for a reel, ad, vlog or short film.
---

# Shoot planning

## 1. Concept → hook → beats

1. One-sentence idea and the single feeling/takeaway.
2. Hook for the first 1-3 s (visual + text).
3. Beats (5-12 for a reel): what each shot shows and why it is there.
4. Ending: payoff, loop back to the start, or CTA.

## 2. Shot list template

| # | Shot | Size/angle | Movement | fps | Duration to record | Notes |
|---|---|---|---|---|---|---|
| S1 | laptop opens, face lit by screen | MCU, eye level | slow push-in | 24 | 10 s | lock focus on face |
| S2 | eye macro | ECU | static | 50/60 | 8 s | slow-mo |

Rules: record 3-5 s of handle before and after every action; shoot every key action twice (wide + close) for match-on-action cuts; record 30 s of room tone per location.

## 3. Camera settings

| Setting | Recommendation | Why |
|---|---|---|
| Resolution | 4K (2160x3840 vertical for reels) | crop/reframe room, sharper after platform compression |
| Frame rate | 24 cinematic, 30 social/screens, 50/60 for slow-mo (play at 40-50%) | motion feel |
| Shutter | 180° rule: 1/(2×fps) → 1/50 at 24-25 fps, 1/60 at 30, 1/100-1/120 at 50-60 | natural motion blur |
| Flicker | in 50 Hz countries (India, Europe, most of Asia/Africa) use 1/50 or 1/100; in 60 Hz (US, Canada, parts of Latin America, Japan west) use 1/60 or 1/120 | lights and screens won't flicker/band |
| ISO | stay at base to ~800 on phones; add light instead of ISO | noise |
| White balance | lock it (e.g. 4300 K mixed indoor, 5600 K daylight, 3200 K tungsten); same value for every shot in a scene | shots match in the grade |
| Focus | manual/lock; use focus peaking | AF hunts in low light |
| Exposure | expose for skin; zebras at 95% for screens/highlights | no clipped faces or screens |
| Profile | Apple Log / S-Log3 / C-Log only if you will grade (needs CST/LUT); else Rec.709/standard | latitude vs effort |
| Codec | ProRes 422 HQ (≈5 GB/min at 4K) if space allows; else HEVC 10-bit | grade headroom |
| Stabilization | off on tripod; standard/active handheld; gimbal for walking | |
| Orientation | hold vertical with rotation lock on for 9:16 | no rotation surprises |
| Audio | external lav/shotgun for dialogue; phone mic only for reference | clean sound |

Phone apps with manual control: Blackmagic Camera (free, iOS/Android), Apple Camera Pro modes, Filmic-style apps.

## 4. Lighting quick rules

- Key light 45° to the side and slightly above; soft (diffused, large source) for faces.
- Separate subject from background with a rim/back light or practical lights behind.
- Screen-lit night look: dim room, screen as key, a small warm practical in background, expose for the face.
- Avoid mixed colour temperatures unless it is the look (teal/orange from screen + lamp).

## 5. Storyboard

For each beat: a thumbnail (sketch, AI image or a frame from a reference), shot size, movement arrow, duration, on-screen text, sound. Keep it to one page for reels. Write it as `storyboard.md` with a table; the edit builds from it.

## 6. Ready-to-shoot checklist

Batteries/storage (40-50 GB free for ProRes 4K), lens cleaned, WB/shutter/fps set per shot list, airplane mode on the phone, test 5 s and check playback for flicker and focus, room tone recorded.
