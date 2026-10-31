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
Actions -> **Daily draft** -> Run workflow (or wait for 08:00 IST). After sending the draft, the run stays alive (up to 5 hours) and publishes within seconds of your Approve tap. It shows as 'in progress' while it waits. When that wait ends, the run starts a follow-up run of **Approve and publish**, which keeps listening for your tap (up to 5.5 hours each, up to 4 in a row: more than Telegram's 24-hour window) and publishes within seconds of the tap while it is active. GitHub runs *scheduled* workflows only every few hours on this repo, however often the schedule says, so the `*/10` schedule is a last resort and cannot be relied on. You can also start **Approve and publish** by hand (Run workflow) to handle a tap that is waiting. If a follow-up cannot be started, your tap is handled at the next scheduled run, which can be hours later.
A draft is marked `publishing` before anything is posted. If a run is killed mid-publish, tapping Approve again will NOT re-post; check your accounts and run Daily draft with *force* if you want a fresh draft.

## Captions and images
**Captions** are short and scannable, not paragraphs: a hook line in CAPITALS and bold, 2-3 short `→` lines, a DM line with the keyword in bold, then hashtags (Instagram). Limits: Instagram image 35-60 words, reel 25-45, Bluesky under 260 characters. LinkedIn is different: plain text, 70-120 words in full sentences, no bold letters, arrows or CAPS lines (`config/voice.md`, "LinkedIn format"), and a second model edits it for clarity. If the writer overshoots it is asked once to shorten. The format lives in `config/voice.md` ("Caption format") and the writer prompt.
- Instagram and Bluesky have no real bold, so emphasis is Unicode bold letters (like 𝗧𝗵𝗶𝘀). It is applied last, after fact-check and ad-review, on at most 6 short spans, never on hashtags, handles or links. Trade-off: screen readers spell it out and bold words are not searchable. `UNICODE_BOLD=0` (a variable) keeps the CAPITALS but drops the bold.

**Images** are now a topic-specific AI picture (a concrete scene, not an empty background) with the hook, tag and DM pill drawn on top in real fonts (image models garble lettering, so they are never asked for text), 1080x1350. Chat cards (customer-message posts) are still the designed chat card. If no AI engine works you get the designed text card, then a plain card. `IMAGE_VISUALS=0` goes back to text cards only.
- **Permanent quality prompt:** `config/image_style.json` has a `quality_suffix` that is appended to *every* prompt sent to Cloudflare FLUX, Gemini and Pollinations (inside each engine, so none can skip it). Edit it there; keep it positive (say what you want, not what to avoid).
- Honest limit: a prompt cannot add pixels. The suffix pushes the model toward sharper, more detailed output; actual resolution comes from asking each engine for portrait size (FLUX at its maximum 8 steps, Gemini with a 4:5 ratio, Pollinations 1080x1350), a sharpening pass after upscaling, and saving at the best JPEG quality that stays under 900 KB. Picture cards carry the IPTC "AI generated" marker.
## Virality hint (advisory)
Every draft gets a coarse **virality hint** from the vendored `viralsim/` package: a 0-100 score per platform, a backlash-risk flag and the top 2-3 writing levers for Instagram. It appears as one line in the Telegram draft message and is saved on the draft (`virality`). **It never blocks, rewrites or ranks anything.** It runs offline (numpy + scipy only, about 2 seconds) and uses your real follower counts and reach from `data/analytics.json`.
- Honest limit: offline it scores wording with a lexical heuristic, and on its own 50-campaign backtest it did not beat a constant guess (`viralsim/README.md`, "Read this before trusting a number"). The simulated reach is in model units: for a 10-follower account it shows hundreds while real posts reach single digits. Read the score as a rough ordering and the levers as writing hints.
- The stored `reach_p10/p50/p90` exist so predicted and real reach can be compared once enough posts have 48h numbers. Do that before letting the score influence anything.
- If it fails, the daily run continues and the Telegram warnings say why (`virality: ...`). To remove it, delete the `virality` stage in `src/run_daily.py`.
- Licences and attribution for the bundled code and data are in `viralsim/NOTICE.md` (the persona pool is CC BY 4.0; `viralsim/signals.py` adapts constants from a project with no licence file, so confirm that before redistributing).

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

## Service explainer diagrams (a supporting image, never the thumbnail)
`src/diagrams.py` draws a colourful, structured diagram of the day's service in code (crisp text, no AI picture) and sends it to Telegram as its own image before the Approve message. It is never posted automatically: use it as a 2nd slide, a comment image or a story. It is drawn into a temp file, so nothing is stored in the repo.
- **Facts only.** The content comes from `config/services.json` and `config/service_details.json` (the packages, copied from the website for now; edit that file to change them). No prices, no payment wording, no "free", no delivery times and no brand line are ever drawn; the only thing at the bottom is the DM button. A layout that needs package details is refused when there are none, so nothing can be invented.
- **Layouts rotate by date, with a different colour palette every day:** stacked steps, a timeline, a hub, a checklist and package cards. Package cards (and the hub and checklist) only appear for services with details. `animated_ads` has no packages on the site, so it uses the steps and timeline layouts.
- **Lead generation has no packages:** its diagram only says to send a message to enquire (`"inquiry_only": true`).

## Carousel posts (hook, problem, solution, CTA)
Every post is a carousel: Instagram and LinkedIn get every slide, Bluesky gets 4 (its maximum, shown as a grid): the hook, the first problem slide, the first solution slide and the CTA. The Telegram draft shows the whole album before you approve.
- **One fixed order, enforced by code** (`src/agents/carousel.py`): 1 hook slide, 1-2 problem slides, 2-3 solution slides, then 1 CTA slide (the service diagram may add one more solution slide). A carousel in any other order, with the wrong counts, over-long text or a banned claim is rejected and re-planned once; if it still fails the post goes out as a single image and the draft says why.
- **Tastes** (`config/carousel_flavors.json`) change HOW each part is told: a strong hook with a slow reveal, a myth bust, a common mistake, a short imaginary scene, a direct question, signs you need it, a "stop doing this", a before/after example, how it works (with the diagram slide) and a factual hook from a verified source. They rotate (never the same one in the last two carousels) and the taste is saved on the draft and compared in the weekly learning review ("Carousel tastes").
- **The "X said ..." taste only uses facts you verified.** A model must never invent who said what, so it runs only when `config/facts.json` lists a fact for the service (exact claim wording, source name, link). The slides must name that source and quote the claim exactly. No facts are shipped, so this taste stays off until you add some. Every other taste is blocked from attributing anything to a study, survey, expert or report.
- **Safety rules on every slide:** no prices, payment words, "free", delivery times, percentages, multipliers or guarantees; a second model fact-checks the whole carousel; if that check is unavailable the draft warns you to read every slide.
- **Look:** slide 1 is the hook image in the day's visual family; the other slides are drawn by code in the same colour, with a role label, slide counter, progress bar and swipe cue.
- **Publishing:** only Buffer, Zernio and Bluesky-direct can post several images, so only they are used for a carousel; if they all fail, the hook image is posted on its own. LinkedIn's text-only days stay text-only, and Wednesday's Instagram stays your manual reel.
- **Switch and storage:** set the repository variable `CAROUSEL` to `0` to go back to one image per post. Slides are hosted from the repo, so media older than 30 days is deleted automatically (git history still keeps old files: expect roughly 1 MB of history per day).

## Image style (consistent look, never a copy)
`config/image_style.json` holds a shared `style_dna` and five visual families (`variants`) written from reference images, as abstract style only: no reference image, text or artwork is stored. Each picture uses ONE family (never the same one twice in a row, otherwise the least used), takes at most two of its elements, and must add ONE new element from that day's topic, so pictures match in style but are never copies. The AI picture contains no text; the headline is added in real fonts. If the model's prompt is unusable, a concrete scene for the service is used with the same style. The family is saved on the draft (`image.style_id`) and compared in the weekly learning review ("Image styles"). The family's accent colour (`accent_rgb`) also colours the headline highlight, glow and DM button of every card, including the designed chat card, and the family is recorded for those cards too. A chat mock-up card is only used for the chatbot service, because it reads as a chatbot ad.

**Service fit guard.** Before a post becomes an image, a second model checks which service a reader would expect the topic and hook to be selling (`src/agents/fit.py`). A confident mismatch (for example a chatbot pain with a blog button) re-runs the analysis once with a correction, then falls back to the curated idea for the service; if it still drifts, the Telegram draft says so. A failing check never blocks the pipeline. To change the look, edit that file: keep it positive, with no text, numbers or layout words in it.

## Learning loop (what to test next, from your own results)
Deterministic code in `src/learning.py`; the agents only receive its conclusions as guidance, and nothing edits prompts, rules or code. You still approve every post.
1. **Join and freeze.** Every 6 hours the analytics sync stores each published post's numbers once it is 48 hours old (and again at 7 days) in `data/post_results.json`, with what was tested: problem, angle type, hook style, format, CTA.
2. **Score.** Each post is compared with the account's own median for the same platform and format (reach, engagement per reach, and skip rate when known). A weak post is diagnosed: **distribution** (few people saw it), **hook** (people left fast), **value** (they stayed but did not engage) or **mixed**. With fewer than 3 comparable posts, or under 100 followers, results are labelled hints.
3. **Problem bank.** `data/problem_bank.json` holds audience problems researched by a model (hypotheses until a post tests them), each `untested`, `testing`, `promising`, `winner` or `dud`. A problem is only a dud after 2 tests whose diagnosis was about content, never because nobody saw the posts.
4. **One variable at a time.** Each day's draft starts from an EXPERIMENT: mostly repeat a problem that worked and change only its angle type or hook style (alternating), and about 1 post in 3 test a new problem with the best known hook style. The Telegram draft says what is being tested.
5. **Weekly review** (Mondays 09:00 IST, `weekly-review.yml`): a Telegram summary of what was tested, what the numbers say, the next planned experiments, and which numbers are missing. `data/learning_notes.md` has the full table.
6. **Screenshots and images sent to the bot.** A photo is never used as the post image by accident, and nothing is saved or committed until its purpose is clear. Caption `stats` (or `stats linkedin`, `stats instagram`) = analytics screenshot; caption `post` or `ai` = today's post image (`ai` also marks it AI-generated). With any other caption, or none, the bot asks "What is this image?" with two buttons (use as today's post image / it's analytics). When no draft is waiting for an image, a plain photo is read as analytics.
   Analytics screenshots: Gemini reads the numbers, the bot replies with what it read, and they fill gaps the APIs cannot (LinkedIn posts published through Buffer, reel retention). A screenshot never overwrites a number an API reported. Needs `GEMINI_API_KEY` on the Approve workflow.
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
