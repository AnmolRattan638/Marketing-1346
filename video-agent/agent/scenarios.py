"""Before / after scenarios for the before-after template.

BEFORE = a business with no website and no digital marketing, connected to the two problems owners feel: sales and finding customers.
AFTER  = the same business with a website + chatbot, connected to the same two problems.
Every line is a capability or a situation, never a guaranteed result, a number or a client story (hard rule: no invented results). Short on purpose:
the template prints them at small size and splits items on commas, so no commas inside a line."""
SCENARIOS = {
    "default": {
        "beforeTitle": "Website nahi, marketing nahi",
        "beforeItems": "Customers aapko dhoondh nahi paate,Sales sirf walk-ins pe tiki hai,Raat ki enquiry miss ho jaati hai",
        "afterTitle": "Website + chatbot",
        "afterItems": "Google pe customers aapko dhoondhte hain,Chatbot turant reply deta hai,Har enquiry aapke paas save hoti hai",
    },
}


def pick(service: str | None = None) -> dict:
    return dict(SCENARIOS.get(service or "", SCENARIOS["default"]))


def target_index(voiced: list) -> int | None:
    """Which scene shows the before/after: the payoff beat, else the recap beat, else a late scene (never the hook or the CTA)."""
    for want in ("payoff", "recap"):
        for i, v in enumerate(voiced):
            if v[1].get("beat") == want:
                return i
    n = len(voiced)
    return int(n * 0.6) if n >= 4 else None


def spec(service: str | None = None) -> dict:
    """The props of the portrait before/after board (graphics/BeforeAfter.tsx): lists instead of comma strings."""
    s = pick(service)
    split = lambda x: [i.strip() for i in x.split(",") if i.strip()]
    return {"beforeTitle": s["beforeTitle"], "beforeItems": split(s["beforeItems"]), "afterTitle": s["afterTitle"], "afterItems": split(s["afterItems"])}


# Device demos for the fix beat. Illustrative, generic copy (no client, price or result); the chat shows what a chatbot does, the site what an enquiry looks like.
CHAT = {"title": "Aapka Business", "messages": [
    {"from": "customer", "text": "Aapki service ka rate kya hai?"},
    {"from": "bot", "text": "Namaste! Apni requirement bhejiye, hum aapko turant details dete hain."},
    {"from": "customer", "text": "Raat ko bhi reply milega?"},
    {"from": "bot", "text": "Ji haan, chatbot 24x7 jawab deta hai."}]}
SITE = {"url": "aapkabusiness.in", "headline": "Aapka business, ab Google pe", "sub": "Services, kaam aur contact ek jagah", "button": "Enquiry bhejein", "toast": "Nayi enquiry mili"}


def demo_target(voiced: list, avoid: int | None) -> int | None:
    """The fix beat, else the scene after the hook, never next to the before/after scene or the last (CTA) scene."""
    n = len(voiced)
    order = [i for i, v in enumerate(voiced) if v[1].get("beat") == "fix"] + ([1] if n >= 4 else [])
    for i in order:
        if i != avoid and (avoid is None or abs(i - avoid) > 1) and 0 < i < n - 1:
            return i
    return None


def demo_kind(service: str | None, seed: str) -> str:
    """chatbot -> phone chat, website -> browser; any other service alternates by day so reels differ."""
    if service == "chatbot":
        return "chat"
    if service == "website":
        return "site"
    return "chat" if sum(map(ord, seed)) % 2 else "site"


# The hook's missed-message pile (generic, illustrative, no figures): shows the pain of leads arriving while nobody answers.
HOOK_NOTIFS = ["WhatsApp: Rate kya hai?", "Missed call: naya customer", "Instagram DM: Aap kal khule ho?"]
