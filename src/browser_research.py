"""Browser research: open the top sources in headless Chromium and read the full article, so the fact sheet works from the page itself, not a 2-line snippet.
Off unless BROWSER_RESEARCH=1 and Playwright + Chromium are installed (the daily workflow does that). Never raises: a page that fails keeps its snippet.
Page text is UNTRUSTED: it is cleaned like any web text and only ever reaches the fact-checker as facts-only evidence."""
import os
import sys

from . import web_research

MAX_PAGES = 4
MAX_CHARS = 3500
TIMEOUT_MS = 15000
JS = "() => { const el = document.querySelector('article') || document.querySelector('main') || document.body; return el ? el.innerText : ''; }"


def enabled():
    return os.getenv("BROWSER_RESEARCH", "").strip().lower() in ("1", "true", "yes")


def _read(page, url):
    page.goto(url, timeout=TIMEOUT_MS, wait_until="domcontentloaded")
    return page.evaluate(JS) or ""


def enrich(items, read=None, max_pages=MAX_PAGES):
    """items from web_research -> same items, the first `max_pages` with a `text` field holding the cleaned article body. `read(url)` is injectable for tests."""
    if not enabled() or not items:
        return items
    out = [dict(i) for i in items]
    pw = ctx = None
    try:
        if read is None:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.launch()
            ctx = browser.new_context(user_agent="Mozilla/5.0 (compatible; research-bot)")
            page = ctx.new_page()
            read = lambda url: _read(page, url)
        done = 0
        for it in out:
            if done >= max_pages:
                break
            try:
                text = web_research._clean(read(it["url"]), MAX_CHARS)
            except Exception as e:
                web_research.PROBLEMS.append(f"browser research: {it.get('domain')} failed ({str(e)[:80]})")
                continue
            if len(text) > len(it.get("snippet") or "") + 200:
                it["text"] = text
                done += 1
    except Exception as e:
        web_research.PROBLEMS.append(f"browser research unavailable ({str(e)[:100]})")
        print(f"[browser] {e}", file=sys.stderr)
        return items
    finally:
        try:
            if ctx:
                ctx.browser.close()
            if pw:
                pw.stop()
        except Exception:
            pass
    return out
