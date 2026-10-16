"""Pull analytics from every configured platform into data/analytics.json. Run by the Analytics sync workflow."""
from . import analytics, learning


def main():
    data = analytics.sync()
    for name, s in data["sources"].items():
        state = {True: "ok", False: "FAILED: " + str(s["error"]), None: "not configured"}[s["ok"]]
        print(f"[{name}] {state}")
    for p, cov in data["coverage"].items():
        print(f"[{p}] " + (f"via {cov['source']}" + (f" ({cov['note']})" if cov.get("note") else "") if cov["ok"] else f"no live data: {cov['note']}"))
    try:
        learning.update_results(data)        # learning loop: freeze each post's 48h / 7d numbers (never breaks the sync)
    except Exception as e:
        print(f"[learning] results not updated: {e}")
    text, signals = analytics.digest(data)
    print(f"{len(data['posts'])} posts, {len(signals)} weak signals")
    print(text)


if __name__ == "__main__":
    main()
