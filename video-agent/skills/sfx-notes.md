# Sound and reel craft

Adapted (MIT) from the suggest-sfx skill (hassancs91/claude-youtube-editor), video-editing-skills (sound-design, style-instagram-reels) and
Ultimate-Video-Editing-Skills (sfx-guide, audio-mixing). The sounds are the CC0 SFX Kit. You choose only the KIND of sound and the MOMENT. The code
picks the exact file, starts it so its hit lands on that frame, and sets its level under the voice. Never ask for volume: the finished reel is
normalised to -14 LUFS by code.

- Function first. Ask what the moment needs: a visible move or wipe -> whoosh; a word or element appearing (emphasis) -> pop; a press, tap or snap -> click;
  tension building to a reveal word -> riser; a landing or hard stop -> impact (rare, once in a reel at most).
- Sync to the word, not roughly near it: `at_word` must be a word that is really spoken in that scene. A riser needs about a second of run-up, so never
  put one on a word in the first second of a scene.
- Less is more. One hint per scene at most, none in some scenes, about 6-8 sounds in a 30 s reel. The code adds the sounds that belong to graphics
  (a stat landing, a title) on its own, so do not repeat them. Never a sound on a plain cut.
- Silence is a tool: no effect right before the payoff line makes the payoff hit harder.
- Reel craft: the first frame is already the hook (no slow fade-in, no logo first); something changes (a new picture, a camera move or a graphic) at
  least every 3 seconds; the hook line leads; end on the payoff or echo the hook's words so it loops; keep text inside the safe area (x 60-940,
  y 250-1500) and never in the bottom 20%; where the voice is the moment, add no effect.
