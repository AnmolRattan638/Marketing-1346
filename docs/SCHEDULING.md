# Making the daily runs start on time

GitHub's own `schedule:` is not reliable for this repository. Measured on 19 Nov 2026: the draft set for 08:00 IST started at 16:00 IST, the "every 10 minutes" approval check ran about every 8 hours, and the "every 6 hours" analytics sync ran twice a day. Scheduled runs on a quiet repository are the first to be delayed, and nothing in the workflow files can change that.

The reliable fix is a small outside timer that tells GitHub to start the run at the exact time. The workflows are safe to start more than once: a second start finds today's work already done and stays quiet, so the old GitHub schedule can stay as a backup.

## One-time setup (about 5 minutes, free)

1. **Create a token.** GitHub, Settings, Developer settings, Personal access tokens, Fine-grained tokens, Generate new token. Repository access: only `Marketing-1346`. Permission: Actions, Read and write. Copy the token.
2. **Create two jobs on cron-job.org** (free; any service that can send a timed HTTP POST works). Set the timezone to Asia/Kolkata.

| Job | Time | URL |
|---|---|---|
| Reel 1 + carousel draft | 08:00 every day | `https://api.github.com/repos/AnmolRattan638/Marketing-1346/actions/workflows/daily-draft.yml/dispatches` |
| Reel 2 | 17:00 every day | `https://api.github.com/repos/AnmolRattan638/Marketing-1346/actions/workflows/second-reel.yml/dispatches` |

For both: method POST, body `{"ref":"main"}`, and these headers:

```
Authorization: Bearer <your token>
Accept: application/vnd.github+json
Content-Type: application/json
```

A success returns HTTP 204 (no body). Keep the token private: it can start workflows in this repository.

## What each run does

- **Daily draft (08:00):** carousel, captions and reel 1 (same script). You approve the carousel in Telegram and post reel 1 yourself.
- **Second reel (17:00):** a different service, its own research, verified facts and script, then its own video. It arrives in Telegram as "Reel 2 of today". Post it yourself.
- Starting either one again the same day does nothing (`data/master/<date>-2.json` and `data/drafts/<date>.json` mark the day as done). Use "Redo" in the manual run form to force it.
