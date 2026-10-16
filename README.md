# Marketing-1346: autonomous marketing for AR Designs

Daily pipeline: **strategist -> research (Gemma) -> analysis (GPT-OSS 120B) -> writer (Gemini) -> fact-check -> ad-check -> image + reel idea -> Telegram approval -> Buffer (Instagram, LinkedIn, Bluesky)**.
Nothing is posted until you tap **Approve** in Telegram.

## Setup
Repo -> Settings -> Secrets and variables -> Actions -> add **secrets**:

| Secret | Where from |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio (Gemini + Gemma) |
| `GROQ_API_KEY` | console.groq.com (GPT-OSS 120B) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | your bot / your chat |
| `BUFFER_API_KEY` | publish.buffer.com/settings/api |
| `ZERNIO_API_KEY` | zernio.com/dashboard/api-keys (starts with `sk_`) |
| `UPLOAD_POST_API_KEY`, `UPLOAD_POST_USER` | Upload-Post dashboard -> API Keys; `USER` is your Upload-Post profile name |

**More secrets (all optional, a missing one is skipped):**

| Secret | Used for |
|---|---|
| `NVIDIA_API_KEY` | Only for non-`:free` Nemotron IDs. The default `nvidia/nemotron-3-ultra-550b-a55b:free` runs through OpenRouter (`OPENROUTER_API_KEY`); on failure GPT-OSS on Groq answers (strategist) |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | Image generation (FLUX on Workers AI), else a free fallback |
| `OPENROUTER_API_KEY` | Fallback model when another provider returns 429 |
| `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD` | Direct Bluesky posting (joins the rotation) |
| `LIMESOCIAL_API_KEY`, `LIMESOCIAL_INSTAGRAM_USERNAME` | Lime Social publisher, Instagram only (needs an image). Username as shown in its dashboard |
| `SOCIALAPI_KEY` | SocialAPI.ai publisher (key starts `sapi_key_`; Instagram + LinkedIn, not Bluesky) |

Variables (Variables tab): `NVIDIA_MODEL`, `OPENROUTER_MODEL`, `FACTCHECK_PROVIDER` (groq / nvidia / gemini / openrouter), `FACTCHECK_MODEL`, `PUBLISHER_ORDER` (see below).

**Telegram safety:** only the owner can approve. In a private chat this works automatically. If `TELEGRAM_CHAT_ID` is a group, approvals are refused until you add `TELEGRAM_ALLOWED_USER_ID` (your own Telegram user id) as a secret or variable.
Instagram: auto-posted image + caption every day except Wednesday (set in `config/services.json` -> `instagram.manual_reel_weekdays`); on Wednesday you post the reel yourself from the 3 Flow prompts.

By default publishers rotate daily (first choice changes each day) and each platform falls back to the next tool if one fails. A tool with no secrets is skipped.
To use fixed tools instead (recommended once one tool works well for you, because posting to one account through many tools can look odd to a platform), set the variable `PUBLISHER_ORDER`, e.g. `buffer,zernio`: only those tools are used, in that order, with no rotation. Names: `buffer`, `zernio`, `upload-post`, `limesocial`, `socialapi`, `bluesky-direct`. Note: all tools publish immediately (Buffer posts are sent with shareNow, falling back to a post scheduled 2 minutes ahead, never the Buffer queue).

LinkedIn has its own order: it always goes through Buffer first (other tools only if Buffer fails), while Instagram and Bluesky keep the rotation or your `PUBLISHER_ORDER`. To change it, set the variable `LINKEDIN_PUBLISHER_ORDER` (e.g. `buffer`, or `buffer,zernio`); then only those tools are used for LinkedIn.

Optional **variables**: `GEMMA_MODEL`, `GROQ_MODEL`, `GEMINI_MODEL` (to change model IDs).

Telegram: approvals are polled with `getUpdates`, so the bot must have **no webhook** set (`/deleteWebhook`).

**The repo must stay public.** Images are served to the posting tools from `raw.githubusercontent.com`, and the Daily draft run waits up to 5 hours for your tap (about 150 runner-hours a month), which is free only on public repos. Everything under `data/` (drafts, metrics, strategy) is therefore public too: never put anything private in it. The daily run sends a Telegram warning if GitHub reports the repo as private.

## Run
Actions -> **Daily draft** -> Run workflow (or wait for 08:00 IST). After sending the draft, the run stays alive (up to 5 hours) and publishes within seconds of your Approve tap. It shows as 'in progress' while it waits. **Approve and publish** is only a safety net for taps made after that window (it checks every 10 minutes); it skips itself while Daily draft is running.
A draft is marked `publishing` before anything is posted. If a run is killed mid-publish, tapping Approve again will NOT re-post; check your accounts and run Daily draft with *force* if you want a fresh draft.

## Captions and images
**Captions** are short and scannable, not paragraphs: a hook line in CAPITALS and bold, 2-3 short `→` lines, a DM line with the keyword in bold, then hashtags (Instagram). Limits: Instagram image 35-60 words, reel 25-45, Bluesky under 260 characters. LinkedIn is different: plain text, 70-120 words in full sentences, no bold letters, arrows or CAPS lines (`config/voice.md`, "LinkedIn format"), and a second model edits it for clarity. If the writer overshoots it is asked once to shorten. The format lives in `config/voice.md` ("Caption format") and the writer prompt.
- Instagram and Bluesky have no real bold, so emphasis is Unicode bold letters (like 𝗧𝗵𝗶𝘀). It is applied last, after fact-check and ad-review, on at most 6 short spans, never on hashtags, handles or links. Trade-off: screen readers spell it out and bold words are not searchable. `UNICODE_BOLD=0` (a variable) keeps the CAPITALS but drops the bold.

**Images** are now a topic-specific AI picture (a concrete scene, not an empty background) with the hook, tag and DM pill drawn on top in real fonts (image models garble lettering, so they are never asked for text), 1080x1350. Chat cards (customer-message posts) are still the designed chat card. If no AI engine works you get the designed text card, then a plain card. `IMAGE_VISUALS=0` goes back to text cards only.
- **Permanent quality prompt:** `config/image_style.json` has a `quality_suffix` that is appended to *every* prompt sent to Cloudflare FLUX, Gemini and Pollinations (inside each engine, so none can skip it). Edit it there; keep it positive (say what you want, not what to avoid).
- Honest limit: a prompt cannot add pixels. The suffix pushes the model toward sharper, more detailed output; actual resolution comes from asking each engine for portrait size (FLUX at its maximum 8 steps, Gemini with a 4:5 ratio, Pollinations 1080x1350), a sharpening pass after upscaling, and saving at the best JPEG quality that stays under 900 KB. Picture cards carry the IPTC "AI generated" marker.
## Analytics sync (so the strategist sees what is weak)
The **Analytics sync** workflow runs every 6 hours (and on demand) and writes `data/analytics.json`: per-post numbers, follower counts and a daily follower history. The Daily draft run reads it (read-only), hands the strategist a short digest plus a list of **weak signals** found by plain rules (not by an LLM), and puts the top two in your Telegram draft message and in `data/account_state.json`.

| Platform | Where the numbers come from | What you need |
| --- | --- | --- |
| Bluesky | Bluesky's public API | nothing new: `BLUESKY_HANDLE` (if that secret is an email, set the variable `BLUESKY_PUBLIC_HANDLE` to `name.bsky.social`) |
| Instagram | Instagram Graph API (reach, views, likes, comments, shares, saves; reel skip rate and watch time) | secret `IG_ACCESS_TOKEN`: a long-lived Instagram User token with `instagram_business_basic` and `instagram_business_manage_insights`. Without it, Instagram falls back to Zernio. |
| LinkedIn | Zernio's analytics API | `ZERNIO_API_KEY` with analytics on your Zernio plan. LinkedIn only reports posts published *through Zernio*. |

Good to know:
- **Missing is not zero.** A number a platform did not report is shown as `n/a` and never counted as zero. Meta can lag up to 48 hours, so posts under 24 hours old are not judged.
- **LinkedIn without Zernio:** there is no automatic route (LinkedIn's own post-analytics API needs an approval). Put your numbers in `data/metrics.json` by hand; the strategist reads them.
- **Instagram token:** it lasts 60 days. The sync tries to extend it weekly and sends a Telegram alert if it expires, cannot be extended, or comes back as a different string (then create a new one and update the secret). Tokens never go into `analytics.json`.
- **Failures:** one platform failing never stops the others. The last good numbers are kept and marked stale, and you get one Telegram alert after the second failure in a row.
- **Zernio plan:** Zernio's docs disagree on whether analytics is included or an add-on. If your plan does not have it, the sync reports that clearly (Actions log, and Telegram after two failed runs) and the rest keeps working.
- `data/analytics.json` is public like everything in `data/`. It only changes (and only creates a commit) when a number changed or a new day starts.
- Manual stats in `data/metrics.json` still matter for what no API gives you (DMs, WhatsApp enquiries, LinkedIn without Zernio).

## Learning loop (what to test next, from your own results)
Deterministic code in `src/learning.py`; the agents only receive its conclusions as guidance, and nothing edits prompts, rules or code. You still approve every post.
1. **Join and freeze.** Every 6 hours the analytics sync stores each published post's numbers once it is 48 hours old (and again at 7 days) in `data/post_results.json`, with what was tested: problem, angle type, hook style, format, CTA.
2. **Score.** Each post is compared with the account's own median for the same platform and format (reach, engagement per reach, and skip rate when known). A weak post is diagnosed: **distribution** (few people saw it), **hook** (people left fast), **value** (they stayed but did not engage) or **mixed**. With fewer than 3 comparable posts, or under 100 followers, results are labelled hints.
3. **Problem bank.** `data/problem_bank.json` holds audience problems researched by a model (hypotheses until a post tests them), each `untested`, `testing`, `promising`, `winner` or `dud`. A problem is only a dud after 2 tests whose diagnosis was about content, never because nobody saw the posts.
4. **One variable at a time.** Each day's draft starts from an EXPERIMENT: mostly repeat a problem that worked and change only its angle type or hook style (alternating), and about 1 post in 3 test a new problem with the best known hook style. The Telegram draft says what is being tested.
5. **Weekly review** (Mondays 09:00 IST, `weekly-review.yml`): a Telegram summary of what was tested, what the numbers say, the next planned experiments, and which numbers are missing. `data/learning_notes.md` has the full table.
6. **Screenshots.** Send the bot an analytics screenshot with the caption `stats` (or `stats linkedin`, `stats instagram`). Gemini reads the numbers, the bot replies with what it read, and they fill gaps the APIs cannot (LinkedIn posts published through Buffer, reel retention). A screenshot never overwrites a number an API reported. Needs `GEMINI_API_KEY` on the Approve workflow.
Trade-off: LinkedIn only reports posts published through Zernio, so LinkedIn posts sent through Buffer have no automatic numbers. Either send the screenshot or set the variable `LINKEDIN_PUBLISHER_ORDER` to `zernio`.

## Idea bank (hooks that stop the scroll)
`config/ideas.json` holds a **hook library**, **reel rules** and 16 **post ideas** (2-3 per service), adapted from vidIQ's public guidance (its "18 Viral Hooks for YouTube Shorts" and "9 Video Ideas to Go Viral" guides, and its 2026 niche list where AI-tool explainers rank among the most-shared formats). vidIQ is YouTube-focused, so its entertainment topics are deliberately *not* copied: only hook mechanics and formats that fit the brand rules in `services.json` (no demos, no invented results, no single niche, no absolute claims). I could only use vidIQ's public pages; its dashboard needs a login.
- **Research** is offered up to 4 unused ideas for today's service and must adapt at least 2; it returns the `idea_id`. **Analysis** writes hooks from the hook library. The chosen `idea_id` is saved in the draft, and an idea is not offered again once a draft used it.
- **Reel scripts** now follow vidIQ's reel rules: the hook lands in about 1 second (not 3), the first frame stacks a payoff visual + 3-7 words of on-screen text + a 5-10 word spoken line, no greeting, works on mute, and the ending hands back to the opening so a replay feels natural.
- Add your own ideas to the `ideas` list (copy an existing entry; `hook` must be 12 words or fewer). Ideas are used in file order.
- Honest limit: vidIQ says viral is not the same as profitable. These formats are a better *starting point* for attention; whether they bring DMs is something your analytics will show.

## LinkedIn: alternate text-only and image posts
LinkedIn alternates a **text-only** post and a post **with the image** (your first, text-only post reached more people than the later image posts). The format is decided when the draft is made: it flips the last LinkedIn post that actually went out (a failed or unapproved post does not count), is saved in the draft as `linkedin_format`, and shows in the Telegram message ("LinkedIn today: TEXT ONLY (no image)").
- On a text day the writer is told there is no picture: no "see the image", and the first line must carry the whole hook because LinkedIn hides the rest behind "see more". The publisher then leaves the picture off LinkedIn **only**; Instagram and Bluesky still get it.
- Pin it with the variable `LINKEDIN_FORMAT` = `text` or `image` (default `alternate`).
- The learning loop and the analytics digest label each LinkedIn post with this format, so a text post is compared with other text posts and an image post with other image posts. Two posts are not enough to prove text beats image (they also differed in topic and age); a few weeks of alternating will show whether it holds.

## Tests
`tests/*_test.py` run offline (no keys, no network): `for t in tests/*_test.py; do python $t; done`. The **CI** workflow runs pyflakes and these tests on every push and pull request.

## Files
- `config/voice.md`, `config/services.json`: your voice and the facts the agents may use. **Edit these first.**
- `data/history.json`, `data/strategy.md`, `data/metrics.json`: state the agents learn from.
- `src/agents/*`: one file per agent; prompts live there.

## Known limits
- Google Flow has no API: the reel idea is sent to Telegram for you to generate manually.
- Images come from a free generator and are served to Buffer via this repo's raw URLs, so the repo must stay public.
- Every week or two, update `data/metrics.json` by hand: views, average watch time, skip rate, shares, comments, DMs. The strategist uses it to tune the hooks. Keep the existing shape: an `instagram` object with `followers`, `posts`, `views_last_30_days`, `bio`, `posts_by_views` and `reel_insights`. No Instagram API is used (it needs a Business/Creator account).
- The Instagram `bio` in `metrics.json` is read by the strategist and checked against the rules in `config/services.json`. A bio that names one niche or region, or promises a timeframe, will be flagged. Keep the real bio there so the check is honest.
- History: `data/history.json` plus every file in `data/drafts/` count as "already used", so a draft you rejected by editing its file is not repeated.

## Using your own design (e.g. Adobe Express)
Send a photo (or an image file) to the bot while a draft is pending. It becomes today's image for Instagram, LinkedIn and Bluesky; then tap Approve. Add the caption `ai` if the image is AI-generated so the AI marker is embedded.
