---
name: style-instagram-reels
description: Instagram Reels / TikTok / YouTube Shorts editing style - vertical 9:16 short-form built for retention - 1-second hook, beat-synced cuts, punchy on-screen text and captions inside the UI safe zone, loopable endings, trending audio workflow, cover frame, and export specs per platform. Use when the user wants a reel, short, TikTok, or any vertical social video.
---

# Style: Instagram Reels / TikTok / Shorts

Load with: `editing-foundations`, `beat-sync`, `captions-typography`, `ffmpeg-pipeline` (+ `color-grading`, `sound-design` as needed).

## Signature

- 9:16, 1080x1920 (or 2160x3840 for a sharper upload), 30 fps (24 for cinematic reels).
- 7-30 s for reach; 30-90 s only when the story holds (tutorials, stories).
- Hook in the **first second**: movement + bold text or a strong line. No logos, no slow fades in.
- Cuts every 0.8-2 s, on beats/hits; fast bursts before the drop.
- Text on screen most of the time (many watch muted); captions for speech.
- Ending that loops back to the start or ends on the payoff (rewatch = retention).

## Formats that work (pick one)

| Format | Structure |
|---|---|
| Hook → payoff | text question/claim 0-2 s, build 2-10 s, payoff on drop |
| Transformation / before-after | "before" 1-3 s → smash/transition on hit → "after" |
| POV / relatable | POV text overlay + a single relatable moment, 5-10 s |
| Two moods / contrast | calm A → bars/smash → chaotic B (or reverse) on the song switch |
| Listicle / tips | hook, 3-5 tips each 2-4 s with numbered text, CTA |
| Story-time | talking head + captions + B-roll, jump cuts, 30-60 s |
| Aesthetic montage | 6-12 shots on beats, minimal text (see `style-aesthetic-minimal`) |
| Trend/template | follow the trend's timing exactly (see `reference-matching`) |
| Quote reel | footage + hand-lettered quote stack (see `reel-hand-text`) |

## Build recipe

1. Pick the song window (7-20 s, downbeat to downbeat) and run `beats.py`.
2. Assign shots to beats: hero shot on the drop, strongest motion in the first second.
3. Crop to 9:16 around the subject (track it if it moves). Never letterbox a reel unless it's a deliberate cinematic frame.
4. Grade consistently (one look across all shots).
5. Text: hook headline 0-2.5 s (90-140 px at 1080w), then captions or beat-timed words. Inside safe zone **x 60-940, y 250-1500**.
6. Transitions: hard cuts on beats + 1-2 signature transitions (whip, flash, zoom) on hits only.
7. Sound: music + 4-10 SFX tied to visible events.
8. Export: H.264 High, 1080x1920 or 2160x3840, 30 fps, CRF 16-18, AAC 48 kHz 320k, `+faststart`, -14 LUFS.

## Trending audio

The in-app sound is licensed only in the app. Deliver:
1. `*_silent.mp4` (or with very low guide audio) for upload; user adds the sound in-app at the same start point.
2. `*_with_sound.mp4` for review.
Note the exact song start second in the delivery message.

## Platform deltas

| | Instagram Reels | TikTok | YouTube Shorts |
|---|---|---|---|
| Length sweet spot | 7-30 s | 15-45 s | 20-50 s (max 3 min) |
| Bottom UI | tallest (caption + audio) | tall | medium |
| Cover | choose frame or upload 1080x1920; grid shows centre 3:4/4:5 | choose frame | choose frame |
| Captions | in-video recommended | in-video or auto-captions | in-video recommended |

## Cover frame

Make a cover with the hook text inside the centre 1080x1350 (profile grid crop). Export a still at 1080x1920.

## Quality bar

- First frame is already interesting (check frame 0).
- No text in the bottom 20% or under the right-side buttons.
- Every cut on its beat frame (verified).
- Readable at 360 px wide.
- Loudness -14 LUFS, true peak ≤ -1 dBTP.

## Lessons from real reels

- Generic motivational reels get reach but few follows; personal story, humor and niche-relevant reels convert better. Suggest a story angle when the content allows it.
- Dev/creator humor ("2 AM one more bug") outperforms pure aesthetic for shares.
- Keep the account's visual voice consistent (same fonts, grade, caption style) across reels.
