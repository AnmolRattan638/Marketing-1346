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
To use fixed tools instead (recommended once one tool works well for you, because posting to one account through many tools can look odd to a platform), set the variable `PUBLISHER_ORDER`, e.g. `buffer,zernio`: only those tools are used, in that order, with no rotation. Names: `buffer`, `zernio`, `upload-post`, `limesocial`, `socialapi`, `bluesky-direct`. Note: Buffer queues the post, the others publish immediately.

Optional **variables**: `GEMMA_MODEL`, `GROQ_MODEL`, `GEMINI_MODEL` (to change model IDs).

Telegram: approvals are polled with `getUpdates`, so the bot must have **no webhook** set (`/deleteWebhook`).

**The repo must stay public.** Images are served to the posting tools from `raw.githubusercontent.com`, and the Daily draft run waits up to ~5h40m for your tap (about 170 runner-hours a month), which is free only on public repos. Everything under `data/` (drafts, metrics, strategy) is therefore public too: never put anything private in it. The daily run sends a Telegram warning if GitHub reports the repo as private.

## Run
Actions -> **Daily draft** -> Run workflow (or wait for 08:00 IST). After sending the draft, the run stays alive (up to ~5h40m) and publishes within seconds of your Approve tap. It shows as 'in progress' while it waits. **Approve and publish** is only a safety net for taps made after that window (it checks every 10 minutes); it skips itself while Daily draft is running.
A draft is marked `publishing` before anything is posted. If a run is killed mid-publish, tapping Approve again will NOT re-post; check your accounts and run Daily draft with *force* if you want a fresh draft.

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
