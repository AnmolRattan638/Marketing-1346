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

Variables (Variables tab): `NVIDIA_MODEL`, `OPENROUTER_MODEL`, `FACTCHECK_PROVIDER` (groq / nvidia / gemini / openrouter), `FACTCHECK_MODEL`.
Instagram: auto-posted image + caption every day except Wednesday (set in `config/services.json` -> `instagram.manual_reel_weekdays`); on Wednesday you post the reel yourself from the 3 Flow prompts.

Publishers rotate daily (first choice changes each day) and each platform falls back to the next tool if one fails. A tool with no secrets is skipped.

Optional **variables**: `GEMMA_MODEL`, `GROQ_MODEL`, `GEMINI_MODEL` (to change model IDs).

Telegram: approvals are polled with `getUpdates`, so the bot must have **no webhook** set (`/deleteWebhook`).

## Run
Actions -> **Daily draft** -> Run workflow (or wait for 08:00 IST). After sending the draft, the run stays alive (up to ~5h40m) and publishes within seconds of your Approve tap. It shows as 'in progress' while it waits. **Approve and publish** is only a safety net for taps made after that window; it skips itself while Daily draft is running.

## Files
- `config/voice.md`, `config/services.json`: your voice and the facts the agents may use. **Edit these first.**
- `data/history.json`, `data/strategy.md`, `data/metrics.json`: state the agents learn from.
- `src/agents/*`: one file per agent; prompts live there.

## Known limits
- Google Flow has no API: the reel idea is sent to Telegram for you to generate manually.
- Images come from a free generator and are served to Buffer via this repo's raw URLs, so the repo must stay public.
- Every week or two, copy per-reel numbers into `data/metrics.json`: views, average watch time, skip rate, shares, comments, DMs. The strategist uses them to tune the hooks.
- `data/metrics.json` is filled manually (e.g. `{"followers": 8, "likes": 0, "posts": 4}`); the strategist reads it to judge the account's state. No Instagram API is used (it needs a Business/Creator account).

## Using your own design (e.g. Adobe Express)
Send a photo (or an image file) to the bot while a draft is pending. It becomes today's image for Instagram, LinkedIn and Bluesky; then tap Approve. Add the caption `ai` if the image is AI-generated so the AI marker is embedded.
