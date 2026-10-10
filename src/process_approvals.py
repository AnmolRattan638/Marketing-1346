"""Poll Telegram for Approve/Reject taps and publish approved drafts. Runs every ~15 minutes."""
import datetime as dt
import sys, time
from . import config, publish, tg


def _tail(draft):
    ai_img = (draft.get("image") or {}).get("engine") not in (None, "text_card") and (draft.get("image") or {}).get("path")
    if draft.get("instagram_mode") == "manual_reel":
        s = "\n\nInstagram: post today's reel yourself with the INSTAGRAM caption above. If the video or presenter is AI-generated, switch the AI label on."
    else:
        s = "\n\nInstagram was posted automatically with the image and caption."
    if ai_img:
        s += " The image is AI-generated: check the AI label shows on Instagram and LinkedIn, and switch it on if not."
    return s


def handle(cb):
    if str(cb["message"]["chat"]["id"]) != str(tg.chat_id()):
        return
    action, _, date = cb["data"].partition(":")
    path = config.DRAFTS / f"{date}.json"
    draft = config.load_json(path, None)
    if not draft:
        tg.answer(cb["id"], "Draft not found")
        tg.send(f"Could not find the saved draft for {date}, so nothing was posted. Run Daily draft again from the Actions tab and approve the new message.")
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


def _today():
    return dt.date.today().isoformat()


def pending_today():
    d = config.load_json(config.DRAFTS / f"{_today()}.json", None)
    return bool(d) and d.get("status") == "pending"


def poll(state, timeout):
    """One getUpdates call; handles every Approve/Reject tap it returns."""
    updates = tg.get_updates(state["offset"], timeout)
    for u in updates:
        state["offset"] = u["update_id"] + 1
        if "callback_query" in u:
            try:
                handle(u["callback_query"])
            except Exception as e:
                tg.send(f"Error handling approval: {e}")
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
        updates = tg.get_updates(state["offset"])
    except RuntimeError as e:
        tg.send  # noqa
        raise SystemExit(f"{e}. If a webhook is set on the bot, remove it: https://api.telegram.org/bot<TOKEN>/deleteWebhook")
    for u in updates:
        state["offset"] = u["update_id"] + 1
        if "callback_query" in u:
            try:
                handle(u["callback_query"])
            except Exception as e:
                tg.send(f"Error handling approval: {e}")
    config.save_json(config.DATA / "tg_state.json", state)


if __name__ == "__main__":
    main()
