"""Poll Telegram for Approve/Reject taps and publish approved drafts. Runs every ~15 minutes."""
from . import config, publish, tg


def handle(cb):
    if str(cb["message"]["chat"]["id"]) != str(tg.chat_id()):
        return
    action, _, date = cb["data"].partition(":")
    path = config.DRAFTS / f"{date}.json"
    draft = config.load_json(path, None)
    if not draft:
        tg.answer(cb["id"], "Draft not found")
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
                "\n\nCheck: the image is AI-made. Make sure the AI label / 'AI info' shows on Instagram and LinkedIn; if not, switch it on in the app.")
    else:
        return
    history.append({"date": date, "service": draft["service"], "topic": draft["topic"],
                    "hook_style": draft.get("hook_style"), "status": draft["status"]})
    config.save_json(path, draft)
    config.save_json(config.DATA / "history.json", history)


def main():
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
