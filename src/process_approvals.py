"""Poll Telegram for Approve/Reject taps and publish approved drafts. The Daily draft run waits for the tap; when it ends, follow-up runs of the Approve workflow keep
listening (a chain, because GitHub runs scheduled workflows only every few hours, however often the schedule says)."""
import datetime as dt
import os, subprocess, sys, time
from . import config, publish, tg


def _tail(draft):
    img = draft.get("image") or {}
    ai_img = img.get("path") and img.get("ai_generated", img.get("engine") not in (None, "text_card", "user_upload"))
    if draft.get("instagram_mode") == "manual_reel":
        s = "\n\nInstagram: post today's reel yourself with the INSTAGRAM caption above. If the video or presenter is AI-generated, switch the AI label on."
    else:
        s = "\n\nInstagram was posted automatically with the image and caption."
    if ai_img:
        s += " The image is AI-generated: check the AI label shows on Instagram and LinkedIn, and switch it on if not."
    return s


def authorized(chat, sender):
    """Only the owner may approve or send images. In a private chat the sender is the chat itself. In a group chat nobody is trusted
    unless TELEGRAM_ALLOWED_USER_ID is set to the owner's Telegram user id."""
    if str(chat["id"]) != str(tg.chat_id()):
        return False
    allowed = os.getenv("TELEGRAM_ALLOWED_USER_ID")
    if allowed:
        return sender is None or str(sender.get("id")) == str(allowed)
    if str(chat["id"]).startswith("-"):                     # group / channel and no allowed user configured
        if sender is not None:
            tg.send("Approvals from a group chat are disabled until TELEGRAM_ALLOWED_USER_ID (your own Telegram user id) is set as a secret or variable. Nothing was posted.")
        return False
    return sender is None or str(sender.get("id")) == str(chat["id"])


def handle(cb):
    if not authorized(cb["message"]["chat"], cb.get("from")):
        return
    if str(cb.get("data", "")).startswith(("imgpost:", "imgstats:")):
        return handle_image_choice(cb)
    action, _, key = cb["data"].partition(":")
    date = key[:10]
    path = config.DRAFTS / f"{date}.json"
    draft = config.load_json(path, None)
    if not draft:
        tg.answer(cb["id"], "Draft not found")
        tg.send(f"Could not find the saved draft for {date}, so nothing was posted. Run Daily draft again from the Actions tab and approve the new message.")
        return
    if draft.get("id") and draft["id"] != key:        # a button from an older message: never apply it to a newer draft
        tg.answer(cb["id"], "That button belongs to an older draft. Use the newest message.")
        return
    if draft["status"] == "publishing":
        tg.answer(cb["id"], "Publishing started earlier")
        tg.send(f"Draft {date} was already being published and the run may have been interrupted. Check Instagram, LinkedIn and Bluesky before retrying so nothing is posted twice.")
        return
    if draft["status"] != "pending":
        tg.answer(cb["id"], f"Already {draft['status']}")
        return
    history = config.load_json(config.DATA / "history.json", [])
    if action == "reject":
        draft["status"] = "rejected"
        tg.answer(cb["id"], "Rejected")
        tg.send(f"Rejected {date}. Nothing was posted.")
    elif action == "approve":
        tg.answer(cb["id"], "Publishing...")
        draft["status"] = "publishing"          # saved BEFORE posting: if the run dies mid-publish, the draft can never post a second time
        config.save_json(path, draft)
        res = publish.publish_draft(draft)
        draft["results"] = res
        ok = [p for p, r in res.items() if r["ok"]]
        draft["status"] = "published" if len(ok) == len(res) else ("partial" if ok else "failed")
        tg.send(f"Publish result for {date}: {draft['status']}\n" +
                "\n".join(f"- {p}: {'OK' if r['ok'] else 'FAILED'} ({r['detail']})" for p, r in res.items()) +
                _tail(draft))
    else:
        return
    history.append({"date": date, "service": draft["service"], "topic": draft["topic"],
                    "hook_style": draft.get("hook_style"), "status": draft["status"]})
    config.save_json(path, draft)
    config.save_json(config.DATA / "history.json", history)


def _commit(msg):
    """Push the draft + image to the repo right away (image links for the posting tools need it)."""
    subprocess.run(["bash", "scripts/commit_state.sh", msg], cwd=config.ROOT, check=False)


def _image_file_id(msg):
    if msg.get("photo"):
        return msg["photo"][-1]["file_id"]
    if str((msg.get("document") or {}).get("mime_type", "")).startswith("image/"):
        return msg["document"]["file_id"]
    return None


def _pending_draft():
    return config.load_json(config.DRAFTS / f"{_today()}.json", None)


def save_post_image(file_id, ai=False):
    """Today's POST image from an upload the owner confirmed (caption 'post'/'ai' or the button). Only for a pending draft."""
    today = _today()
    path = config.DRAFTS / f"{today}.json"
    draft = config.load_json(path, None)
    if not draft or draft.get("status") != "pending":
        tg.send("There is no pending draft to attach this image to, so I ignored it.")
        return False
    from .agents import image
    dest = config.MEDIA / f"{today}.jpg"
    image._save(tg.download_file(file_id), dest, ai=ai)
    draft["image"] = {"prompt": None, "path": str(dest.relative_to(config.ROOT)), "engine": "user_upload", "ai_generated": ai}
    config.save_json(path, draft)
    _commit(f"image: {today}")
    tg.send("Image received and saved as today's POST image. Tap Approve and it will be used.")
    return True


def handle_message(msg):
    """A photo or image file. Caption 'stats' (e.g. 'stats linkedin') = analytics screenshot; caption 'post' or 'ai' = today's post image ('ai' also marks it
    AI-generated). Anything else is ambiguous, so the bot asks with two buttons and saves nothing (and commits nothing) until you answer."""
    if not authorized(msg["chat"], msg.get("from")):
        return
    file_id = _image_file_id(msg)
    if not file_id:
        return
    cap = (msg.get("caption") or "").strip()
    words = cap.lower().split()
    if cap.lower().startswith("stats"):
        return handle_stats(file_id, cap)
    if "post" in words or "ai" in words:
        return save_post_image(file_id, ai="ai" in words)
    draft = _pending_draft()
    if not draft or draft.get("status") != "pending":      # no post is waiting for an image, so this can only be analytics
        return handle_stats(file_id, cap)
    key = draft.get("id") or _today()
    tg.send("What is this image?", [{"text": "Use as today's post image", "callback_data": f"imgpost:{key}"},
                                    {"text": "It's analytics", "callback_data": f"imgstats:{key}"}], reply_to=msg.get("message_id"))


def handle_image_choice(cb):
    """The answer to 'What is this image?'. The photo is read from the message the question replied to, so nothing was stored before the answer."""
    action, _, key = cb["data"].partition(":")
    file_id = _image_file_id(cb["message"].get("reply_to_message") or {})
    if not file_id:
        tg.answer(cb["id"], "I can no longer find that image")
        tg.send("I could not find that image any more. Send it again with the caption 'post' (today's post image) or 'stats' (analytics).")
        return
    if action == "imgstats":
        tg.answer(cb["id"], "Reading it as analytics...")
        return handle_stats(file_id, "stats")
    draft = config.load_json(config.DRAFTS / f"{key[:10]}.json", None)
    if not draft or draft.get("status") != "pending" or (draft.get("id") and draft["id"] != key):
        tg.answer(cb["id"], "That draft is no longer waiting for an image")
        tg.send("That draft is no longer waiting for an image, so nothing was changed.")
        return
    tg.answer(cb["id"], "Saving...")
    save_post_image(file_id, ai=False)


def handle_stats(file_id, caption):
    """Analytics screenshot (caption 'stats' or 'stats linkedin'): read the numbers, save them for the learning loop, say what was read."""
    from . import vision
    try:
        entry = vision.read_screenshot(tg.download_file(file_id), caption)
    except Exception as e:
        tg.send(f"I could not read that screenshot ({str(e)[:160]}). Nothing was saved.")
        return
    if entry["posts"] or entry["account"]:
        vision.save(entry)
        _commit(f"stats screenshot: {_today()}")
    tg.send(vision.summary(entry))


def _today():
    return dt.date.today().isoformat()


def pending_today():
    d = config.load_json(config.DRAFTS / f"{_today()}.json", None)
    return bool(d) and d.get("status") == "pending"


def poll(state, timeout):
    """One getUpdates call; handles every Approve/Reject tap and every image you sent to the bot."""
    updates = tg.get_updates(state["offset"], timeout)
    for u in updates:
        state["offset"] = u["update_id"] + 1
        try:
            if "callback_query" in u:
                handle(u["callback_query"])
            elif "message" in u:
                handle_message(u["message"])
        except Exception as e:
            tg.send(f"Error handling that message: {e}")
    config.save_json(config.DATA / "tg_state.json", state)


def _notify(text):
    try:
        tg.send(text)
    except Exception as e:                                  # a failed notification must never crash the run
        print(f"[wait] could not send Telegram message: {e}")


def pending_recent(hours=23.5):
    """Is a draft still waiting for a tap that Telegram will still deliver? (Telegram keeps taps for 24 hours.) Uses the draft's created_at; drafts
    from before that field existed count from 03:00 UTC on their date."""
    now = dt.datetime.now(dt.timezone.utc)
    for f in sorted(config.DRAFTS.glob("*.json"))[-3:]:
        d = config.load_json(f, None)
        if not isinstance(d, dict) or d.get("status") != "pending":
            continue
        try:
            made = dt.datetime.fromisoformat(d["created_at"])
        except (KeyError, ValueError, TypeError):
            made = dt.datetime.fromisoformat(f"{d.get('date', f.stem)}T03:00:00+00:00")
        if now - made < dt.timedelta(hours=hours):
            return True
    return False


def wait(seconds, quiet=False):
    """Stay alive after the draft is sent and publish the moment you tap Approve (checks every few seconds).
    Any error (network blip, non-JSON reply, Telegram outage) is logged and retried with a growing pause. If errors never stop,
    the job ends normally and the next follow-up run takes over: the run does not fail. quiet=True skips the 'no decision yet' reminder (used by the follow-up runs)."""
    state = config.load_json(config.DATA / "tg_state.json", {"offset": 0})
    deadline, conflicts, errors = time.time() + seconds, 0, 0
    while time.time() < deadline and pending_recent():
        try:
            poll(state, 25)
            conflicts = errors = 0
        except SystemExit:
            raise
        except RuntimeError as e:
            msg = str(e)
            if "webhook" in msg.lower():
                raise SystemExit(f"{msg}. Remove the webhook: https://api.telegram.org/bot<TOKEN>/deleteWebhook")
            if "conflict" in msg.lower():
                conflicts += 1
                print(f"[wait] {msg}")
                if conflicts == 5:
                    _notify("Another program seems to be reading this Telegram bot's messages (maybe your Aegis agent), so approvals can be missed. Create a separate bot for marketing with @BotFather.")
                time.sleep(15)
            else:
                errors += 1
                print(f"[wait] {msg}")
                time.sleep(min(15 * errors, 120))
        except Exception as e:
            errors += 1
            print(f"[wait] unexpected {type(e).__name__}: {e}")
            time.sleep(min(15 * errors, 120))
        if errors >= 20:
            _notify("Telegram kept failing for this run, so the live wait for your Approve tap ended early. Your draft is saved: tap Approve within 24 hours.")
            return
    if pending_recent() and not quiet:
        _notify(f"No decision on today's draft after {seconds // 3600}h {seconds % 3600 // 60}m. It stays saved: tap Approve within 24 hours.")


def main():
    if "--still-pending" in sys.argv:                        # exit code 0 = a draft is still waiting for a tap (used to chain the follow-up runs)
        sys.exit(0 if pending_recent() else 1)
    if "--wait" in sys.argv:
        return wait(int(sys.argv[sys.argv.index("--wait") + 1]), quiet="--quiet" in sys.argv)
    state = config.load_json(config.DATA / "tg_state.json", {"offset": 0})
    try:
        poll(state, 0)
    except RuntimeError as e:
        raise SystemExit(f"{e}. If a webhook is set on the bot, remove it: https://api.telegram.org/bot<TOKEN>/deleteWebhook")


if __name__ == "__main__":
    main()
