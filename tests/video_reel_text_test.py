"""The script + caption message that follows the reel."""
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import reel_text

plan = {"scenes": [{"narration": "Google: aapka business kahan hai?"}, {"narration": "Prateeksha ke mutabik, over 75% Indians mobile se browse karte hain."},
                   {"narration": "Mobile-first rakho, tez load karo, kyunki customers ek tap se call kar sakte hain."}, {"narration": "Comment SITE likho, tumhe simple website checklist mil sakti hai."}]}
master = {"service": "website", "beats": [{"beat": b} for b in ("pain", "poke", "fix", "cta")], "marketing": {"keyword": "SITE", "gets": "a one-page checklist: the 10 things to check on your site"},
          "facts": [{"source": "prateeksha.com"}, {"source": "sarlie.dev"}, {"source": "prateeksha.com"}]}
s = reel_text.script_text(plan, master)
assert s.startswith("REEL SCRIPT") and "1. Hook: Google: aapka business kahan hai?" in s and "3. Fix: Mobile-first rakho" in s and "4. Ask: Comment SITE" in s
c = reel_text.caption_text(plan, master)
assert c.startswith("GOOGLE: AAPKA BUSINESS KAHAN HAI?") and "→ Prateeksha ke mutabik" in c and "→ Mobile-first rakho" in c
assert "Comment SITE likho, main aapko one-page checklist DM mein bhej dunga." in c, c
assert "Sources: prateeksha.com, sarlie.dev" in c and "#WebsiteDesign" in c and c.count("prateeksha.com") == 1
assert "Comment SITE likho, tumhe" not in c.split("→")[-1].split("\n\n")[0]                     # the CTA is rebuilt as the ask, not pasted twice
m = reel_text.message(plan, master)
assert m.index("REEL SCRIPT") < m.index("CAPTION (copy and paste")
# no master (topic run) and scenes without narration still work
assert "1. Scene 1:" in reel_text.script_text({"scenes": [{"narration": "Ek line"}]}, None)
assert reel_text.message({"scenes": []}, None) == ""
long = reel_text.caption_text({"scenes": [{"narration": "Hook line?"}, {"narration": "x " * 100}, {"narration": "Cta"}]}, {"service": "chatbot", "beats": []})
assert "→" not in long and "#WhatsAppBot" in long                                              # a line too long for a caption is skipped, not cut mid-sentence
print("reel text test passed")
