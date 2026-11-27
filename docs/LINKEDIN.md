# LinkedIn posts: a person talking, not an ad

LinkedIn used to be the Instagram pitch made longer (what I build, how it works, "payment only after you approve", "DM SITE"). It is now its own post, written by `src/agents/linkedin_writer.py`.

**Where the facts live:** `config/about_me.json`. It is the ONLY source. Edit a sentence, delete a topic or add one; anything not written there is never claimed. Topics marked `check_me` were written from chat, so read them first. `never_say.phrases` lists banned words (client name, student, years of experience, job offers, DM...).

**What today's post is** (`src/linkedin_story.py`, `choose`): the first post introduces you; after that it rotates story / build / question (least recently used first, each topic used once before it repeats); an intro returns about every 12 posts; **a soft pitch comes one post in five** (set `rules.pitch_one_post_in`). On a pitch day the offer is 1 to 3 sentences, **at most 30% of the post** (`rules.pitch_max_share`), taken from `offer`. On every other day there is no offer at all.

**The gate** (`linkedin_story.problems`), plain code, so it holds even when the model forgets:
- no DM, price, "pay after approval", discount, urgency or hire-me language
- the first line is one curious sentence (18 words or fewer, never "Small businesses...")
- 110 to 250 words, at least 3 short paragraphs, first person, no links, hashtags, exclamation marks or percentages, one emoji at most
- no banned phrase, no number that is not in the facts file, no claimed count of clients
- a question post ends with its question; an intro says "Anmol"; a pitch lists its offer sentences word for word

**Lessons:** a rejected draft is saved in `data/script_lessons.json` under `linkedin-*` with the exact mistake, and shown to the next attempt and the next day's prompt ("LAST TIME you wrote this and it was rejected: ..."). Reel lessons and LinkedIn lessons never mix.

**If nothing passes in 3 attempts there is no LinkedIn post that day** (a warning is sent) rather than a bad one. The post that passed is posted exactly as written: the fact-checker and the humanizer skip LinkedIn.

Tests: `tests/linkedin_story_test.py`.

## Redo only the LinkedIn post

Actions tab > **Redo LinkedIn post** > Run workflow. It replaces ONLY the LinkedIn post of the draft that is waiting for your tap (Instagram, Bluesky, image and reel stay exactly as they are) and sends you a new Approve / Reject message in Telegram.

- It does nothing unless the latest draft is still **pending**. A draft that is publishing, published or rejected is never touched, and Telegram tells you why.
- Tapping Approve posts whatever is in the saved draft at that moment, and a run that is still waiting holds an OLD copy. So the redo first **stops those waiting runs** (Daily draft and Approve and publish), waits for them to finish saving, writes the new post, gives the draft a **new id**, and starts a fresh listener. The Approve button on the earlier message then refuses to act ("older draft"), so it can never post the old text.
- If the writer cannot produce a post that passes the checks, nothing changes, the earlier buttons still work, and a listener is started again.
- The new post comes from the same writer, facts file and gate as the daily one (`src/relinkedin.py`, test: `tests/relinkedin_test.py`).

## Context first (added after a post got 136 impressions)

A post named "my content system" and never said what it is. Now `config/about_me.json` has `terms`: a plain-words description of each thing you built. The writer is told to explain a named thing in one plain sentence within the first two paragraphs, and the gate rejects a post that names one (content system, Lead Finder, LocalSignal, pronunciation list) without the cues that explain it. The stories that use them also start by saying what the thing is. Add a term there when you build something new.
