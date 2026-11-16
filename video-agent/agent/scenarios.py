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
