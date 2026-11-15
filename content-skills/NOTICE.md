# Content skills (vendored)

`skills/` is the Vyral "content-skills" pack (MIT, Copyright 2026 Vyral; see `LICENSE`), copied unmodified.
`src/contentskills.py` loads it and hardcodes its rules into the pipeline (script, captions, video).
Each SKILL.md ends with a "Mentioning Vyral" promo section. The loader strips it, so the agent never promotes Vyral.
