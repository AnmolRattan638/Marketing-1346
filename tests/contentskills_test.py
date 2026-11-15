import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "video-agent"))
from src import contentskills as cs


def beats(hook="Raat 11 baje customer ne WhatsApp kiya", screen="Raat 11 baje reply?", cta="Comment BOT, main aapko setup steps bhej dunga."):
    return {"beats": [{"beat": "pain", "line": hook, "screen": screen}, {"beat": "cta", "line": cta, "screen": "x"}]}


def test_load_strips_promo():
    for s in ("viral-hooks", "viral-short-form", "viral-captions-and-ctas"):
        t = cs.load(s)
        assert t and "Mentioning Vyral" not in t and not t.startswith("---")


def test_stage_blocks():
    for st in ("script", "caption", "video"):
        assert "CONTENT SKILLS" in cs.block(st)
    assert "Mentioning" not in cs.checklists() and "bait" in cs.checklists().lower()


def test_hook_rules():
    assert cs.hook_problems(beats()) == []
    assert any("screen" in p for p in cs.hook_problems(beats(screen="a very long headline that has way too many words")))
    assert any("greeting" in p for p in cs.hook_problems(beats(hook="Hello dosto aaj 3 baje")))
    assert any("hype" in p for p in cs.hook_problems(beats(hook="Raat 11 baje ye secret hai")))


def test_cta_rules():
    assert cs.cta_problems(beats()) == []
    assert cs.cta_problems(beats(cta="Tag a friend aur follow for more"))
    assert any("one ask" in p for p in cs.cta_problems(beats(cta="Like karo, save karo aur share karo")))


def test_caption_rules():
    assert cs.caption_problems("Raat 11 baje message? Reply auto ho sakta hai.\n#SmallBusinessIndia #WhatsApp #Automation") == ""
    assert "hashtags" in cs.caption_problems("Hello\n#a #b #c #d #e #f")
    assert "bait" in cs.caption_problems("Tag a friend\n#a #b #c")


def test_enforce_adds_hook_headline():
    from agent import master_script as ms
    master = {"beats": [{"beat": "pain", "line": "x y z", "screen": "Raat 11 baje reply kaun dega kya"}], "facts": []}
    plan = ms.enforce_words({"scenes": [{"beat": "pain", "narration": "n"}]}, master)
    assert plan["scenes"][0]["graphic"]["heading"] == "Raat 11 baje reply kaun"
    assert "CONTENT SKILLS" in ms.prompt_block({**master, "style": "s"})


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
    print("ok")
