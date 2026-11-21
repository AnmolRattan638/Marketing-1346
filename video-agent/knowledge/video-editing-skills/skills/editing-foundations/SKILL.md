---
name: editing-foundations
description: Core film and video editing craft that every editing style builds on - cut types (hard, jump, J-cut, L-cut, match, smash, cross-cut, cutaway, cut-in, invisible), transitions, pacing and rhythm, shot sizes and coverage, continuity and the 180-degree rule, hooks and story structures, B-roll. Use when planning or reviewing any edit, choosing transitions, fixing pacing, or explaining editing decisions.
---

# Editing foundations

Rules of thumb from film grammar. Apply them with judgment: every rule can be broken on purpose, never by accident.

## 1. Cut types (what each one says)

| Cut | How | Use it to | Watch out |
|---|---|---|---|
| **Hard / straight cut** | picture and sound change on the same frame | default; 90% of cuts | cut on action or on a beat so it feels motivated |
| **Jump cut** | same framing, time removed | compress talking-head pauses, show passage of time, energy | add a punch-in (105-115% scale) on alternate cuts to hide it when it should feel smooth |
| **J-cut** | next shot's **audio** starts before its picture | lead into a scene, interview answers, natural conversation | 0.3-1.5 s lead is typical |
| **L-cut** | previous shot's **audio** continues over the next picture | let a line land over B-roll or a reaction | keep the audio tail clean (no breath clipped) |
| **Match cut** | shape, motion, colour or action continues across the cut | travel transitions, time jumps, "satisfying" edits | align the matching element to the same screen position (track it) |
| **Match on action** | cut in the middle of a movement from angle A to angle B | invisible continuity in coverage | cut 2-3 frames after the motion starts |
| **Smash cut** | abrupt cut from calm to loud (or reverse) | comedy, shock, contrast ("my two moods") | silence or held frame before it makes the smash louder |
| **Cross-cut / parallel** | alternate between two lines of action | tension, comparison, before/after | shorten intervals as you approach the climax |
| **Cutaway** | cut to something else in the scene, back again | hide edits, show what is being talked about | must relate to the dialogue |
| **Cut-in / insert** | tighter shot of a detail in the same scene | product details, hands, emotion | keep screen direction |
| **Invisible / whip / mask cut** | hide the cut in fast motion, a passing object, or darkness | one-take feel, transitions in reels | needs motion blur on both sides |
| **Montage** | many short shots compress time into one idea | training, travel, process, "day in life" | rhythm from music; each shot shows one idea |

## 2. Transitions (use sparingly)

- A cut is the default transition. Every other transition needs a reason.
- **Dissolve / cross-fade**: time passing, soft mood. 0.5-1.5 s.
- **Dip to black / white**: chapter break (black), flashback or hit (white flash 2-4 frames).
- **Whip pan / zoom blur**: energy, location change; 4-8 frames of directional blur either side of the cut.
- **Light leak / flash**: warm or nostalgic hit on a beat.
- **Glitch / RGB split**: tech, digital, aggressive; 3-6 frames.
- **Push / slide**: graphics-heavy or UI content.
- Never mix many transition families in one piece. Pick 1-2 and repeat them so they read as a style.

## 3. Pacing and rhythm

- Average shot length (ASL) guides: velocity/hype edit 0.2-0.6 s, reels 0.8-2 s, YouTube talking head 2-6 s with B-roll every 5-10 s, cinematic 3-8 s, documentary 4-10 s.
- Vary shot length. A constant length feels mechanical; a long hold after fast cuts lands the moment.
- Cut on **motivation**: an action, a look, a sound, a beat, the end of a thought.
- Leave a beat of air after a punchline or emotional line (0.5-1 s), then cut.
- Trim heads and tails: start a shot as late as possible and leave as early as possible.
- The first 1-3 seconds decide retention on social. Start with the most interesting frame, motion or line, not a logo.

## 4. Shot grammar

- Sizes: extreme wide (establish), wide, medium, medium close-up, close-up, extreme close-up (detail). Change by at least two sizes or 30° of angle between consecutive shots of the same subject, otherwise it looks like a mistake (jump).
- **180-degree rule**: keep the camera on one side of the line of action so screen direction stays consistent.
- **Eyeline and screen direction**: a character exiting right enters the next shot from the left.
- Sequence pattern for a scene: wide → medium → close → detail → reaction.
- B-roll: shoot/choose in sets of 3-5 (wide, medium, close, detail, movement).

## 5. Story structures

- **Hook → Problem → Solution → Proof → CTA**: ads, launches, explainers.
- **Hook → Setup → Payoff**: memes, reels, skits.
- **Thesis → Evidence → Counterpoint → Conclusion**: documentary.
- **Arrival → Highlights → Quiet moment → Departure**: travel and events.
- **Intro → Verse → Chorus → Bridge → Outro**: music-led edits; map visual intensity to song energy.
- **Contrast / two moods**: calm A then chaotic B (or reverse) with a smash or transition at the switch.
- Open loop: tease the payoff in the first seconds ("wait for it", result first, then how).

## 6. Hooks that work in the first 1-3 s

- Result first (final product, transformation), then the process.
- Motion in frame 1 (no static logo, no fade from black on social).
- Bold on-screen text stating the payoff or question.
- A pattern interrupt: unexpected sound, smash cut, extreme close-up.

## 7. Speed and time

- Slow motion needs high-frame-rate source (50/60/120 fps). Conform 60 → 24/30 for real slow motion; do not slow down 30 fps footage below ~70% without optical-flow interpolation (`minterpolate` or Resolve Optical Flow / Speed Warp) or it stutters.
- Speed ramps: ease into and out of speed changes (see `beat-sync`).
- Freeze frame: hold 0.5-2 s with a zoom or a text callout.
- Reverse: useful for "rewind" and satisfying loops.

## 8. Audio is half the edit

- Clean audio beats clean picture. Viewers forgive soft footage, not bad sound.
- Use room tone to fill gaps; never leave digital silence under picture unless it is a deliberate effect.
- Music sets the rhythm; dialogue sets the story. Decide which leads before cutting.

## 9. Review checklist

- Does the first second earn the second second?
- Is every cut motivated? Any accidental jump cuts (same size, small change)?
- Any flash frames (1-frame leftovers) at cut points?
- Does the energy curve rise to a peak and resolve?
- Does it end cleanly (hold last frame ≥ 1 s, or a deliberate loop for reels)?
