# Custom SFX pack (user-supplied, 15 WAVs (v2_glitch removed: it only masked the voice))

Added 2026-11-24 from `sound_effects.zip` (v1 = 7 sounds, v2 = 8 sounds). 44.1 kHz stereo 16-bit, 0.5-3.5 s.

`catalog.json` uses the same field names as `../sfxkit/catalog.json` (`sync_at`, `lufs`, `tags`, ...).
`sync_at` is the loudest moment, auto-detected - listen and correct any that are off (e.g. `v2_cinematic_whoosh`).
`lufs` is measured; there is no `under_voice_db` / `avoid_voice` yet, so treat the hits and risers as avoid-under-voice until set.

Not wired into `agent/sfxkit.py` or `agent/sfx_plan.py` on purpose: `tests/video_sfxkit_test.py` asserts the kit is exactly 320 sounds.
