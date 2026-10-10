import os
import requests


def _api(method, **kw):
    r = requests.post(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}", timeout=60, **kw)
    d = r.json()
    if not d.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {d.get('description')}")
    return d["result"]


def chat_id():
    return os.environ["TELEGRAM_CHAT_ID"]


def send(text, buttons=None):
    chunks = [text[i:i + 3900] for i in range(0, len(text), 3900)] or [""]
    res = None
    for i, c in enumerate(chunks):
        payload = {"chat_id": chat_id(), "text": c}
        if buttons and i == len(chunks) - 1:
            payload["reply_markup"] = {"inline_keyboard": [buttons]}
        res = _api("sendMessage", json=payload)
    return res


def send_photo(path, caption=""):
    with open(path, "rb") as f:
        return _api("sendPhoto", data={"chat_id": chat_id(), "caption": caption[:1000]}, files={"photo": f})


def get_updates(offset, timeout=0):
    return _api("getUpdates", json={"offset": offset, "timeout": timeout, "allowed_updates": ["callback_query"]})


def answer(cb_id, text):
    try:
        _api("answerCallbackQuery", json={"callback_query_id": cb_id, "text": text})
    except Exception:
        pass
