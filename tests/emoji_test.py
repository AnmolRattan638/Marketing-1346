import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import captions
s = open("src/agents/writer.py").read()
s2 = open("src/agents/linkedin_writer.py").read()
assert "EMOJI (instagram and bluesky)" in s and "at most one emoji" in s2 and "no emoji, no hashtags" not in s
out = captions.finalize_posts({"instagram": "Aapki site slow hai 📱 **fix** karo\n\n#web", "linkedin": "Your site loads slowly 🙂 and people leave.", "bluesky": "Small fix, big change 💬"})
assert "📱" in out["instagram"] and "🙂" in out["linkedin"] and "💬" in out["bluesky"], out
print("emoji test passed")
