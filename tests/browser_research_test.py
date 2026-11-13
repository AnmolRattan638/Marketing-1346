"""Offline test: browser research adds full text, is off by default, never raises, and the fact sheet can verify a figure only the full text states."""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ.pop("BROWSER_RESEARCH", None)
from src import browser_research as br, web_research as wr
from src.agents import factsheet as fs
items = [{"title": "A", "url": "https://a.com/1", "domain": "a.com", "snippet": "short", "date": None},
         {"title": "B", "url": "https://b.com/2", "domain": "b.com", "snippet": "short", "date": None}]
long_text = "Survey of 500 owners. " * 20 + "Exactly 62% of customers leave after a slow reply. " + "More detail here. " * 20
assert br.enrich(items, read=lambda u: long_text) == items            # off by default
os.environ["BROWSER_RESEARCH"] = "1"
def read(u):
    if "b.com" in u: raise RuntimeError("blocked")
    return long_text
out = br.enrich(items, read=read)
assert "62%" in out[0]["text"] and "text" not in out[1] and "text" not in items[0]
assert any("b.com failed" in p for p in wr.problems())
sheet = fs.build("slow replies", out + [{"title": "C", "url": "https://c.com", "domain": "c.com", "snippet": "x"}] * 0, ask=lambda p, s="", **k: json.dumps({"facts": [
    {"claim": "62% of customers leave after a slow reply", "figure": "62%", "source": 1, "verdict": "verified"}]}))
assert len(sheet["facts"]) == 1 and sheet["facts"][0]["figure"] == "62%"          # verified only because the full page was read
print("browser research ok")
