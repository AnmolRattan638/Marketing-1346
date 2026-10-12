"""Poll Telegram for Approve/Reject taps and publish approved drafts (the Daily draft run waits for the tap; the safety-net workflow polls every 10 minutes)."""
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


def handle_message(msg):
    """A photo/image file sent to the bot becomes today's post image (e.g. a design made in Adobe Express)."""
    if not authorized(msg["chat"], msg.get("from")):
        return
    file_id = None
    if msg.get("photo"):
        file_id = msg["photo"][-1]["file_id"]
    elif str((msg.get("document") or {}).get("mime_type", "")).startswith("image/"):
        file_id = msg["document"]["file_id"]
    if not file_id:
        return
    today = _today()
    path = config.DRAFTS / f"{today}.json"
    draft = config.load_json(path, None)
    if not draft or draft.get("status") != "pending":
        tg.send("There is no pending draft to attach this image to, so I ignored it.")
        return
    from .agents import image
    ai = "ai" in (msg.get("caption") or "").lower().split()      # caption "ai" marks it as AI-generated
    dest = config.MEDIA / f"{today}.jpg"
    image._save(tg.download_file(file_id), dest, ai=ai)
    draft["image"] = {"prompt": None, "path": str(dest.relative_to(config.ROOT)), "engine": "user_upload", "ai_generated": ai}
    config.save_json(path, draft)
    _commit(f"image: {today}")
    tg.send("Image received and saved for today's draft. Tap Approve and it will be used.")


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


def wait(seconds):
    """Stay alive after the draft is sent and publish the moment you tap Approve (checks every few seconds)."""
    state = config.load_json(config.DATA / "tg_state.json", {"offset": 0})
    deadline, conflicts = time.time() + seconds, 0
    while time.time() < deadline and pending_today():
        try:
            poll(state, 25)
            conflicts = 0
        except RuntimeError as e:
            msg = str(e)
            if "webhook" in msg.lower():
                raise SystemExit(f"{msg}. Remove the webhook: https://api.telegram.org/bot<TOKEN>/deleteWebhook")
            conflicts += 1
            print(f"[wait] {msg}")
            if conflicts == 5:
                tg.send("Another program seems to be reading this Telegram bot's messages (maybe your Aegis agent), so approvals can be missed. Create a separate bot for marketing with @BotFather.")
            time.sleep(15)
    if pending_today():
        tg.send(f"No decision on today's draft after {seconds // 3600}h {seconds % 3600 // 60}m. It stays saved: tap Approve within 24 hours and it will post within about 10 minutes.")


def main():
    if "--wait" in sys.argv:
        return wait(int(sys.argv[sys.argv.index("--wait") + 1]))
    state = config.load_json(config.DATA / "tg_state.json", {"offset": 0})
    try:
        poll(state, 0)
    except RuntimeError as e:
        raise SystemExit(f"{e}. If a webhook is set on the bot, remove it: https://api.telegram.org/bot<TOKEN>/deleteWebhook")


if __name__ == "__main__":
    main()
