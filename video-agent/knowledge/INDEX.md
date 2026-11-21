# Knowledge base

Reference copies of three open-source packs (licences next to each). They are NOT loaded into the planner: it reads only three skill files (`skills/`, capped for the free-tier token limits). What the pipeline actually uses is in code or in `skills/sfx-notes.md`, as marked below.

| Pack | Skill | What it covers | Used for |
|---|---|---|---|
| video-editing-skills (MIT) | `beat-sync` | Sync an edit to music - beat, downbeat and onset detection with librosa, building a beat grid, choosing a song window, placing cuts, flashes, text and | **reference only**: reels here are voice-led, not music-cut |
| video-editing-skills (MIT) | `captions-typography` | Captions, subtitles and on-screen text for video - word-level transcription, caption styles (bold pop / Hormozi, karaoke word highlight, natural sente | **reference only**: the pipeline has its own caption system (agent/captions.py, agent/caption_zones.py, template/src) |
| video-editing-skills (MIT) | `color-grading` | Color correction and color grading for video - correction vs grade order, ASC CDL (slope/offset/power), white balance, exposure, contrast curves, log  | **reference only**: the look system (agent/looks.py) already grades |
| video-editing-skills (MIT) | `davinci-resolve` | Editing inside DaVinci Resolve (free or Studio) - project and timeline setup, Cut/Edit/Fusion/Color/Fairlight/Deliver pages, color-managed workflows ( | **reference only**: another editor |
| video-editing-skills (MIT) | `editing-foundations` | Core film and video editing craft that every editing style builds on - cut types (hard, jump, J-cut, L-cut, match, smash, cross-cut, cutaway, cut-in,  | **reference only**: cut-type vocabulary; the planner's own rules already cover hook, pace and payoff |
| video-editing-skills (MIT) | `ffmpeg-pipeline` | Production-correct ffmpeg pipeline for scripted video editing - probing, rotation and VFR fixes, HDR/HLG/Dolby Vision to SDR tone mapping, Apple Log,  | **reference only**: Remotion renders; ffmpeg is used only for probing, clips and the loudness step |
| video-editing-skills (MIT) | `motion-tracking` | Computer-vision helpers for editing with OpenCV - global camera-motion analysis (find pans/rotations vs static parts), stabilization with smoothed cam | **reference only**: no tracked footage in the pipeline |
| video-editing-skills (MIT) | `reel-hand-text` | Put a hand-lettered quote stack on a vertical reel (Instagram/TikTok/Shorts), in the trending style of stacked hand-drawn capitals with mixed word siz | **reference only**: a different text style |
| video-editing-skills (MIT) | `reference-matching` | Recreate the look and rhythm of a reference video ("make it like this reel") - measure its cut times, shot lengths, beat alignment, text timing and po | **reference only**: recreating another reel's timing is not part of the pipeline |
| video-editing-skills (MIT) | `shoot-planning` | Pre-production for videos that will be edited - concept and hook, script, shot list, storyboard, B-roll lists, and camera settings for phones and came | **reference only**: pre-production for real shoots |
| video-editing-skills (MIT) | `sound-design` | Sound design and audio finishing for video edits - music editing (cutting songs on bars, loops, stingers), SFX placement on visible events (whooshes,  | **IN CODE**: SFX placement on the frame, levels under speech and the -14 LUFS target are code: agent/sfxkit.py, agent/sfx_plan.py, agent/finish.py |
| video-editing-skills (MIT) | `style-aesthetic-minimal` | Aesthetic / minimal editing style - calm, slow, curated lifestyle content - desk setups, cafe and study vlogs, slow living, "week in frames", producti | **reference only** |
| video-editing-skills (MIT) | `style-cinematic` | Cinematic editing style - film-like pacing and look for travel films, brand films, short films, cinematic reels and B-roll sequences - 24 fps motion,  | **reference only** |
| video-editing-skills (MIT) | `style-commercial-promo` | Commercial and promo editing style - product ads, restaurant and food promos, real estate tours, local business reels, brand and event announcements,  | **reference only** |
| video-editing-skills (MIT) | `style-documentary` | Documentary editing style - interview-led storytelling for mini-docs, brand stories, case studies, profiles and journalism - story structure from inte | **reference only** |
| video-editing-skills (MIT) | `style-event-highlight` | Event highlight editing style - weddings, engagements, birthdays, concerts, conferences, festivals, college fests and sports recaps - emotional arc fr | **reference only** |
| video-editing-skills (MIT) | `style-explainer` | Explainer and tutorial editing style - software demos, SaaS launch videos, coding tutorials, screen recordings, how-to videos and educational explaine | **reference only** |
| video-editing-skills (MIT) | `style-instagram-carousel` | Instagram carousel and photo-dump editing style - multi-slide 4:5 posts mixing graded photos and short video clips - "week in frames", photo dumps, ed | **reference only** |
| video-editing-skills (MIT) | `style-instagram-reels` | Instagram Reels / TikTok / YouTube Shorts editing style - vertical 9:16 short-form built for retention - 1-second hook, beat-synced cuts, punchy on-sc | **IN THE PLANNER PROMPT**: hook on frame 0, a change every 3 s, loop ending, safe area: distilled into skills/sfx-notes.md (the template already keeps graphics below the logo-safe top, LOGO_SAFE_TOP) |
| video-editing-skills (MIT) | `style-kinetic-typography` | Kinetic typography editing style - text is the main visual - lyric videos, quote reels, word-by-word speech visualisation, typographic intros and ads  | **reference only** |
| video-editing-skills (MIT) | `style-meme-comedy` | Meme and comedy editing style - skits, reaction videos, relatable POV memes, dev/office humor, prank and fail edits - comedic timing, setup/punchline  | **reference only** |
| video-editing-skills (MIT) | `style-motion-graphics` | Motion graphics editing style - designed animation of shapes, type, icons, logos, UI and data - logo stings, animated titles, lower thirds, transition | **reference only** |
| video-editing-skills (MIT) | `style-music-video` | Music video editing style - performance and narrative music videos, lyric/visualizer videos and song-led montages - cutting on bar and phrase structur | **reference only** |
| video-editing-skills (MIT) | `style-talking-head` | Talking-head / creator editing style for YouTube videos, podcasts, educational content and short clips - transcript-driven cutting, jump cuts on silen | **reference only** |
| video-editing-skills (MIT) | `style-trailer` | Trailer and teaser editing style - movie-trailer structure for films, games, products, launches and "my life/my code as a trailer" reels - three-act e | **reference only** |
| video-editing-skills (MIT) | `style-velocity-edit` | Velocity edit / "edit audio" style - high-energy beat-locked edits for cars, sports, gym, gaming, anime, fashion and travel - speed ramps (fast betwee | **reference only** |
| video-editing-skills (MIT) | `style-vfx-compositing` | VFX and compositing editing style - adding things that were not in the shot - tracked text and graphics on surfaces, green-screen keying, CG/3D object | **reference only** |
| video-editing-skills (MIT) | `style-vlog-travel` | Vlog and travel editing style - day-in-the-life vlogs, travel montages, trip recaps and city/nature films - story arc of a journey, match cuts and whi | **reference only** |
| video-editing-skills (MIT) | `video-editing` | Master router for all video editing work. Use whenever the user asks to edit, cut, trim, grade, caption, subtitle, beat-sync, add music or SFX, add mo | **reference only**: router skill for interactive editing sessions |
| Ultimate-Video-Editing-Skills (MIT) | `ultimate-video-editor/SKILL.md` | > | reference only: the master skill |
| Ultimate-Video-Editing-Skills (MIT) | `ai-tools/ai-workflow.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `automation/auto-captions.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `automation/batch-pipeline.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `automation/beat-sync.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `color-science/color-grading-master.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `color-science/lut-equivalent-filters.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `color-science/scene-matching.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `director/choreography.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `director/emotion-mapping.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `director/narrative-structure.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `ffmpeg-recipes/audio-processing.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `ffmpeg-recipes/color-grading.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `ffmpeg-recipes/compositing.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `ffmpeg-recipes/export-presets.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `ffmpeg-recipes/pro-effects.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `ffmpeg-recipes/speed-manipulation.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `ffmpeg-recipes/subtitles.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `ffmpeg-recipes/text-overlays.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `patterns/entrance-exit.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `patterns/state-feedback.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `patterns/transitions.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `programmatic/moviepy-guide.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `programmatic/remotion-guide.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `references/advanced-techniques.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `references/easing-reference.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `references/motion-design.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `references/pitfalls.md` | | **reference only** |
| Ultimate-Video-Editing-Skills (MIT) | `social-media/platform-specs.md` | | **IN CODE**: loudness and delivery targets: agent/finish.py |
| Ultimate-Video-Editing-Skills (MIT) | `social-media/viral-editing.md` | | **IN THE PLANNER PROMPT**: retention rules: distilled into skills/sfx-notes.md |
| Ultimate-Video-Editing-Skills (MIT) | `sound-design/audio-mixing.md` | | **IN CODE**: mix levels and loudness: agent/finish.py and the kit's under-voice levels |
| Ultimate-Video-Editing-Skills (MIT) | `sound-design/sfx-guide.md` | | **IN CODE**: SFX vocabulary and layering: agent/sfxkit.py, agent/sfx_plan.py |
| SFX Kit (CC0) | `sfx-kit/GUIDE.md`, `catalogue.md` | how to find, place and level its 320 sounds | **IN CODE**: the 320 sounds are `assets/sfxkit/` (MP3, levels unchanged) with `catalog.json`; `tools/import_sfx_kit.py` rebuilds them |

Helper scripts shipped inside the skill packs (beat detection, grading, tracking, mixing) are not copied: the pipeline does not run third-party scripts.
