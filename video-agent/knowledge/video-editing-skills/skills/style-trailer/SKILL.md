---
name: style-trailer
description: Trailer and teaser editing style - movie-trailer structure for films, games, products, launches and "my life/my code as a trailer" reels - three-act escalation, title cards on black, dialogue lines as story beats, risers, braams, hits and silence drops, rhythmic cut acceleration, montage climax, logo and date reveal, and button ending. Use for trailers, teasers, launch hype videos, and story-as-trailer social content.
---

# Style: Trailer / Teaser

Load with: `editing-foundations`, `sound-design` (essential), `beat-sync`, `color-grading`, `style-motion-graphics` (title cards).

## Signature

- **Act 1 (setup)**: world and character, calm, longer shots, a single line of dialogue/text.
- **Act 2 (conflict)**: the problem appears; music shifts; cuts quicken; title cards punctuate.
- **Act 3 (climax montage)**: fastest cuts on hits, risers, biggest shots, then **silence drop** (0.5-1.5 s black or held frame).
- **Title/logo reveal** on a hit, then **button**: one last short moment (a joke, a twist) after the title.
- Title cards: white/serif or condensed sans on black, slow push-in or tracking expand; 1.5-2.5 s each; text short ("THIS WINTER", "ONE BUG", "1,250 COMMITS").

## Sound is the trailer

- Trailer music in sections (intro pulse, build, climax). Hits (impacts, braams) on title cards; risers into act changes; whoosh-to-silence before the reveal.
- Dialogue lines placed in gaps of the music; duck music under them.
- Use `sound-design/scripts/sfx.py` for hits/risers/sub booms if no library is available.

## Recipe

1. Write the beat sheet: 5-9 text cards or lines that tell the story.
2. Choose music; mark act boundaries and hits.
3. Build act 1 with 2-4 s shots, act 2 with 1-2 s, act 3 with 0.2-0.6 s on hits.
4. Insert title cards on black between sections, each on a hit.
5. Silence drop → title/logo reveal → date/CTA → button.
6. Grade: higher contrast, consistent; optional letterbox 2.39:1.

## Story-as-trailer social format (worked example)

A developer's git history cut as a movie trailer: title cards set in monospace showing **real** commit hashes, messages and timestamps (git-log yellow hashes, shell-green prompts, late-night hours highlighted orange), a 0 → 1250 commit counter clip, cards centred at ~44% height to stay clear of the Instagram caption UI, intercut with moody night shots graded day-for-night. Everything shown was real data — never fabricate commits, numbers or quotes.

## Quality bar

Every title card readable for ≥ 1.5 s; hits land on the frame; the silence drop is real silence (or near), then the reveal hits hard; ends with a button, not a fade.
