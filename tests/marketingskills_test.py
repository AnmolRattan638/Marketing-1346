import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "video-agent"))
from src import marketingskills as m
from src import contentskills as cs

SV = {s["id"]: s for s in json.load(open(ROOT / "config/services.json"))["services"]}
BOT, SITE, LG = SV["chatbot"], SV["website"], SV["lead_gen"]


def script(cta="Comment BOT likho. Main aapko setup kaise chalega, step by step bhejunga.", hook="Raat 11 baje customer ne WhatsApp kiya, reply nahi mila", extra=""):
    return {"beats": [{"beat": "pain", "line": hook + extra, "screen": "Raat 11 baje reply?"}, {"beat": "fix", "line": "Chatbot turant reply deta hai.", "screen": "x"}, {"beat": "cta", "line": cta, "screen": "DM BOT"}]}


def test_brief_matches_services():
    for sid, c in m.brief()["ctas"].items():
        assert c["keyword"] == SV[sid]["dm_keyword"], sid
        assert c["terms"] and c["gets"]
    assert abs(sum(p["share"] for k, p in m.brief()["pillars"].items() if k != "note") - 100) < 1e-9


def test_pack_vendored_and_clean():
    for s in ("product-marketing", "social", "offers", "copy-editing", "lead-magnets"):
        t = m.load(s)
        assert t and not t.startswith("---") and "Magister" not in t
    assert "Publishing From Your Agent" not in m.load("social") and "tools/REGISTRY" not in m.load("social")
    assert (ROOT / "marketing-skills" / "LICENSE").exists()


def test_block_has_precedence_and_ask():
    b = m.block("script", BOT, "2026-11-17")
    assert "MARKETING BRIEF" in b and "DM BOT" in b and "the brief wins" in b and "AUDIENCE" in b
    assert "ONE story" in m.block("caption", BOT)
    assert m.pillar("2026-11-17") in ("educate", "how_it_works", "offer")


def test_good_script_passes_and_each_break_is_caught():
    assert m.script_problems(script(), BOT) == []
    assert any("offer" in p for p in m.script_problems(script(cta="Comment BOT likho, free demo bhejunga."), BOT))
    assert any("claim" in p for p in m.script_problems(script(extra=", guaranteed"), BOT))
    assert any("keyword" in p for p in m.script_problems(script(cta="Comment SITE likho."), BOT))
    assert any("cta" in p for p in m.script_problems(script(cta="Message kijiye, hum batayenge."), BOT))
    assert any("em dash" in p for p in m.script_problems(script(extra=" — ye dikkat hai"), BOT))
    assert any("contrast" in p for p in m.script_problems(script(extra=". It is not a cost, it is a loss"), BOT))
    off = {"beats": [{"beat": "pain", "line": "Raat 11 baje dukaan band hai", "screen": "x y z"}, {"beat": "cta", "line": "Comment BOT likho.", "screen": "x"}]}
    assert any("off-service" in p for p in m.script_problems(off, {**SV["lead_gen"], "dm_keyword": "LEADS", "id": "website"} if False else {**BOT, "id": "reel_scripts", "dm_keyword": "BOT"}))


def test_hook_is_clean_of_selling():
    assert any("hook" in p for p in m.script_problems(script(hook="AR Designs ka chatbot sirf INR 2999 mein"), BOT))
    assert any("hook" in p or "keyword" in p for p in m.script_problems(script(hook="Comment BOT aur raat 11 baje reply pao"), BOT))
    assert any("ask belongs" in p for p in m.script_problems({"beats": [{"beat": "pain", "line": "Raat 11 baje customer aaya", "screen": "x y z"}, {"beat": "fix", "line": "Comment BOT likho abhi", "screen": "x"}, {"beat": "cta", "line": "Comment BOT likho.", "screen": "x"}]}, BOT))


def test_price_and_audience_rules():
    assert m.text_problems("Chatbot INR 2,999 se shuru", BOT) == []
    assert any("price" in p for p in m.text_problems("Chatbot INR 1,999 mein", BOT))
    assert any("no price" in p for p in m.text_problems("Sheet INR 999 mein", LG))
    assert any("developer" in p for p in m.text_problems("Developers ke liye sheet", LG))
    assert any("freelancers" in p for p in m.text_problems("Freelancers, ye chatbot lo", BOT))


def test_caption_rules():
    ok = "Raat 11 baje message aaya aur reply nahi gaya?\n\nChatbot turant jawab deta hai. DM **BOT** likho.\n#SmallBusinessIndia"
    assert m.caption_problems(ok, BOT) == ""
    assert "BOT" in m.caption_problems("Raat 11 baje message?\nChatbot jawab deta hai.\n#a", BOT)
    assert "keyword" in m.caption_problems("Chatbot jawab deta hai. DM SITE likho.\n#a", BOT)
    assert "em dash" in m.caption_problems("Chatbot — jawab deta hai. DM BOT.\n#a", BOT)


def test_alignment_across_outputs():
    cap = "Chatbot jawab deta hai. DM BOT likho."
    slides = [{"role": "hook", "headline": "Raat 11 baje?", "body": "Customer ka message"}, {"role": "cta", "headline": "DM BOT", "body": "Chatbot reply"}]
    assert m.alignment_problems(BOT, script(), cap, slides, {"scenes": [{"narration": "Chatbot reply. DM BOT."}]}) == []
    bad = m.alignment_problems(BOT, script(), "Chatbot jawab. DM SITE likho.", slides)
    assert any("SITE" in p for p in bad) and any("shared ask" in p for p in bad)
    assert any("price" in p for p in m.alignment_problems(BOT, script(), cap + " INR 1,999", slides))
    assert any("off-service" in p for p in m.alignment_problems(BOT, script(), "DM BOT. Kal subah milte hain", slides))


def test_carousel_rules():
    ok = [{"role": "hook", "headline": "Raat 11 baje?", "body": "Customer ne chatbot se poocha"}, {"role": "cta", "headline": "DM BOT", "body": "Setup kaise hota hai"}]
    assert m.carousel_problems(ok, BOT) == []
    ok[0]["body"] = "Free discount demo"
    assert m.carousel_problems(ok, BOT)


def test_content_and_marketing_agree_on_the_same_script():
    s = script()
    assert cs.problems(s) == [] and m.script_problems(s, BOT) == []
    assert "demo" not in (ROOT / "src/agents/scriptwriter.py").read_text().split("def repair_missing")[1].split("def run")[0].replace("never a demo or sample", "")


def test_prompt_wiring():
    from agent import master_script as ms
    master = {"beats": [{"beat": "pain", "line": "x y z", "screen": "a b c", "visual": "v"}], "style": "s", "marketing": {"keyword": "BOT", "gets": "advice", "pillar": "educate"}}
    pb = ms.prompt_block(master)
    assert "MARKETING (hardcoded" in pb and "DM BOT" in pb
    src = (ROOT / "src/agents/scriptwriter.py").read_text()
    assert "marketingskills.block('script'" in src and "marketingskills.script_problems" in src and "marketingskills.audit" in src
    assert "marketingskills.block('caption'" in (ROOT / "src/agents/writer.py").read_text()
    assert "marketingskills.carousel_problems" in (ROOT / "src/agents/carousel.py").read_text()
    assert "marketingskills.alignment_problems" in (ROOT / "src/run_daily.py").read_text()


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
    print("ok")
