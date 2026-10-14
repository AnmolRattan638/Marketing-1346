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

**The repo must stay public.** Images are served to the posting tools from `raw.githubusercontent.com`, and the Daily draft run waits up to 5 hours for your tap (about 150 runner-hours a month), which is free only on public repos. Everything under `data/` (drafts, metrics, strategy) is therefore public too: never put anything private in it. The daily run sends a Telegram warning if GitHub reports the repo as private.

## Run
Actions -> **Daily draft** -> Run workflow (or wait for 08:00 IST). After sending the draft, the run stays alive (up to 5 hours) and publishes within seconds of your Approve tap. It shows as 'in progress' while it waits. **Approve and publish** is only a safety net for taps made after that window (it checks every 10 minutes); it skips itself while Daily draft is running.
A draft is marked `publishing` before anything is posted. If a run is killed mid-publish, tapping Approve again will NOT re-post; check your accounts and run Daily draft with *force* if you want a fresh draft.

## Captions and images
**Captions** are short and scannable, not paragraphs: a hook line in CAPITALS and bold, 2-3 short `→` lines, a DM line with the keyword in bold, then hashtags (Instagram). Limits: Instagram image 35-60 words, reel 25-45, LinkedIn 70-120 (one sentence per line), Bluesky under 260 characters. If the writer overshoots it is asked once to shorten. The format lives in `config/voice.md` ("Caption format") and the writer prompt.
- Instagram, LinkedIn and Bluesky have no real bold, so emphasis is Unicode bold letters (like 𝗧𝗵𝗶𝘀). It is applied last, after fact-check and ad-review, on at most 6 short spans, never on hashtags, handles or links. Trade-off: screen readers spell it out and bold words are not searchable. `UNICODE_BOLD=0` (a variable) keeps the CAPITALS but drops the bold.

**Images** are now a topic-specific AI picture (a concrete scene, not an empty background) with the hook, tag and DM pill drawn on top in real fonts (image models garble lettering, so they are never asked for text), 1080x1350. Chat cards (customer-message posts) are still the designed chat card. If no AI engine works you get the designed text card, then a plain card. `IMAGE_VISUALS=0` goes back to text cards only.
- **Permanent quality prompt:** `config/image_style.json` has a `quality_suffix` that is appended to *every* prompt sent to Cloudflare FLUX, Gemini and Pollinations (inside each engine, so none can skip it). Edit it there; keep it positive (say what you want, not what to avoid).
- Honest limit: a prompt cannot add pixels. The suffix pushes the model toward sharper, more detailed output; actual resolution comes from asking each engine for portrait size (FLUX at its maximum 8 steps, Gemini with a 4:5 ratio, Pollinations 1080x1350), a sharpening pass after upscaling, and saving at the best JPEG quality that stays under 900 KB. Picture cards carry the IPTC "AI generated" marker.

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
