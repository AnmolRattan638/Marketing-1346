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
    "website": {
        "beforeTitle": "Website nahi",
        "beforeItems": "Google pe aapka naam nahi dikhta,Customer ko bharosa kahan se aaye,Details ke liye sirf phone ka raasta",
        "afterTitle": "Simple website",
        "afterItems": "Google pe aapka business milta hai,Rate timing location ek jagah,Mobile pe tez khulti hai",
    },
    "chatbot": {
        "beforeTitle": "Sirf haath se reply",
        "beforeItems": "Raat ke message subah tak pade rehte hain,Same sawal baar baar likhne padte hain,Customer dusre business ke paas chala jaata hai",
        "afterTitle": "WhatsApp chatbot",
        "afterItems": "Turant jawab mil jaata hai,Timing aur rate khud bata deta hai,Zaroori baat aapko forward hoti hai",
    },
    "animated_ads": {
        "beforeTitle": "Sirf photo wale posts",
        "beforeItems": "Scroll karte log ruk nahi paate,Kaam samjhane mein der lagti hai,Post bina kisi action ke nikal jaati hai",
        "afterTitle": "Short animated ad",
        "afterItems": "Pehle second mein dhyan pakadta hai,Kaam kuch seconds mein dikh jaata hai,Ant mein ek saaf next step",
    },
    "lead_gen": {
        "beforeTitle": "Haath se prospect dhoondhna",
        "beforeItems": "Ghanton search karte rehna,Numbers alag alag jagah bikhre,Pehle kise contact karein pata nahi",
        "afterTitle": "Daily lead sheet",
        "afterItems": "Naye local businesses ek sheet mein,Naam number aur kami saath mein,Pehle kise contact karein saaf dikhta hai",
    },
    "reel_scripts": {
        "beforeTitle": "Camera ke saamne atak jaana",
        "beforeItems": "Kya bolna hai samajh nahi aata,Pehli line mein hi log nikal jaate hain,Reel bina plan ke ban jaati hai",
        "afterTitle": "Ready reel script",
        "afterItems": "Pehli line dhyan pakadti hai,Har line ka ek kaam hota hai,Ant mein ek hi saaf ask",
    },
    "seo_blogs": {
        "beforeTitle": "Google pe blog nahi",
        "beforeItems": "Customer ke sawal ka jawab nahi,Competitor ka page upar dikhta hai,Search se naye log nahi aate",
        "afterTitle": "Sawal jawab wale blog",
        "afterItems": "Customer ka sawal aapke page par,Seedhi bhasha mein jawab,Padhne ke baad contact ka raasta",
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


def demo_kind(service: str | None, seed: str) -> str | None:
    """chatbot -> phone chat, website -> browser. Any other service gets NO chat or website mock-up (they contradict it): its demo scene is a step card from DEMO_STEPS."""
    if service == "chatbot":
        return "chat"
    if service == "website":
        return "site"
    return None


# Demo scene for the services that have no phone/browser picture: a step card with a checklist about THAT service (capabilities, no figures, no results).
DEMO_STEPS = {
    "animated_ads": {"kicker": "Ek ad ka dhancha", "heading": "SHORT AD PLAN", "items": ["Pehle 3 second: customer ki dikkat", "Phir aapka kaam, dikhaya hua", "Ant mein ek saaf next step"]},
    "lead_gen": {"kicker": "Daily sheet", "heading": "LEAD SHEET", "items": ["Business ka naam aur number", "Website ya Instagram ki kami", "Pehle kise contact karein"]},
    "reel_scripts": {"kicker": "Script ka dhancha", "heading": "5 LINE SCRIPT", "items": ["Pehli line: dhyan pakdo", "Beech mein: ek wajah", "Ant mein: ek ask"]},
    "seo_blogs": {"kicker": "Blog ka idea", "heading": "CUSTOMER KA SAWAL", "items": ["Google mein jo sawal likhte hain", "Seedha jawab ek page par", "Padhne ke baad contact ka raasta"]},
}

# The hook's pile of unanswered things, per service (illustrative, no figures). The old single list was WhatsApp-only and showed up on every service.
HOOK_NOTIFS_BY = {
    "chatbot": ["WhatsApp: Rate kya hai?", "Missed call: naya customer", "Instagram DM: Aap kal khule ho?"],
    "website": ["Google: aapka business kahan hai?", "Customer: website ka link bhejiye", "Missed call: naya customer"],
    "animated_ads": ["Instagram: scroll... scroll... scroll", "Aapki post: 2 second mein skip", "Customer: ye kya bechte hain?"],
    "lead_gen": ["Search: restaurants Dehradun", "Sheet 1: 40 naam, 0 number", "Aaj ke prospects: abhi tak 0"],
    "reel_scripts": ["Camera on... ab kya bolun?", "Draft 3: phir delete", "Reel: 2 second mein skip"],
    "seo_blogs": ["Google: best cafe near me", "Customer ka sawal: jawab kahan?", "Competitor ka page: sabse upar"],
}
HOOK_NOTIFS = HOOK_NOTIFS_BY["chatbot"]
_SERVICE = None


def use(service: str | None) -> None:
    """Called once per reel so every graphic of that reel speaks about its own service."""
    global _SERVICE
    _SERVICE = service


def hook_notifs() -> list:
    return list(HOOK_NOTIFS_BY.get(_SERVICE or "", HOOK_NOTIFS_BY["chatbot"]))
