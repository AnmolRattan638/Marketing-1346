"""Pronunciation list: symbols and glued forms the voice used to misread (24x7, 30sec, 24hrs, 1st, 4K, 5G, #1, 10+, 10-15, 5kg, 3,199, phone numbers, www/.com/@),
the words in shortforms.json (acronyms, titles, shorthand), and three old corruptions (money ate the space after it, w/ hit inside show/hide, 4K read as 4 thousand). No network."""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "video-agent"))
from agent import speech_text as st

def say(s): return st.clean(s)

# 1. 24x7 in every spelling is "twenty four by seven"; a date is not
for w in ["24x7", "24X7", "24×7", "24*7", "24 x 7", "24-7", "24by7", "24/7", "24 / 7"]:
    assert say(f"Humari team {w} available hai") == "Humari team twenty four by seven available hai.", (w, say(w))
assert say("24/7/365 uptime") == "twenty four by seven by three sixty five uptime."
assert say("Date 24/7/2026 ko") == "Date 24/7/2026 ko." and say("12-11-2026 ko") == "12-11-2026 ko."
# 2. digits glued to a unit
assert say("30sec mein ready") == "30 second mein ready." and say("24hrs mein delivery") == "24 hours mein delivery." and say("2mins me") == "2 minutes me."
assert say("5kg aur 2GB") == "5 kilogram aur 2 gigabyte."
# 3. ordinals, ranges, plus, hash
assert say("1st, 2nd, 3rd tip") == "first, second, third tip." and say("21st tarikh") == "twenty first tarikh."
assert say("10-15 minutes") == "10 to 15 minutes." and say("9-5 job") == "9 to 5 job." and say("10-15% off") == "10 to 15 percent off."
assert say("10+ saal ka experience") == "10 plus saal ka experience." and say("100%+ growth") == "100 percent plus growth."
assert say("#1 website") == "number 1 website."
# 4. money: the space after the amount survives (it used to become 'rupeesmein'), commas go, /month and /- are said, a range is said
assert say("₹999 mein website") == "999 rupees mein website." and say("Rs 3,199 only") == "3199 rupees only." and say("rs 500 only") == "500 rupees only."
assert say("Sirf ₹999.") == "Sirf 999 rupees." and say("₹1,00,000 ka kharcha") == "100000 rupees ka kharcha." and say("₹5L ka budget") == "5 lakh rupees ka budget."
assert say("₹999/month sirf") == "999 rupees per month sirf." and say("₹999/- only") == "999 rupees only." and say("999/- only") == "999 rupees only."
assert say("₹999-₹3199 tak") == "999 rupees to 3199 rupees tak." and say("$50 per month") == "50 dollars per month."
assert say("5k leads") == "5 thousand leads." and say("4k leads aaye") == "4 thousand leads aaye."            # k stays thousand
# 5. letters, not thousand/times
assert say("4K video banao") == "four K video banao." and say("shoot in 4K") == "shoot in four K." and say("5G ka zamana") == "five G ka zamana." and say("3D design") == "three D design."
# 6. slashes: whole words only (w/ used to eat the end of show/hide and new/old)
assert say("w/ discount") == "with discount." and say("w/o discount") == "without discount." and say("A/B testing karo") == "A B testing karo." and say("and/or") == "and or."
assert "ith" not in say("show/hide button") and "ith" not in say("new/old") and say("show/hide button") == "show ya hide button."
# 7. web addresses, handles, phone numbers
assert say("arrdesigns.com pe aao") == "arrdesigns dot com pe aao." and say("www.arrdesigns.com/contact") == "W W W dot arrdesigns dot com slash contact."
assert say("mail: hello@arrdesigns.com") == "mail, hello at the rate arrdesigns dot com." and say("@arrdesigns follow karo") == "at arrdesigns follow karo."
assert say("https://arrdesigns.in") == "arrdesigns dot in." and say("site.co.in") == "site dot co dot in."
assert say("call 9876543210") == "call 9 8 7 6 5, 4 3 2 1 0." and say("call +91 98765 43210") == "call plus 9 1, 9 8 7 6 5, 4 3 2 1 0."
# 8. words: acronyms letter by letter, titles, shorthand, B2B (was in the list but never worked)
assert say("UPI aur GST") == "U P I aur G S T." and say("GMB profile") == "G M B profile." and say("ChatGPT use karo") == "Chat G P T use karo."
assert say("B2B aur b2c clients") == "B two B aur B two C clients." and say("D2C brand") == "D two C brand."
assert say("Dr. Sharma ka clinic") == "Doctor Sharma ka clinic." and say("Mr. Rao aur Mrs. Rao") == "Mister Rao aur Missus Rao." and say("Pvt Ltd company") == "private limited company."
assert say("e.g. hotels, i.e. local") == "for example hotels, that is local."
# 9. a full stop that ENDS a sentence is kept after an abbreviation or acronym; one inside an abbreviation is dropped
assert say("Accept karo UPI. Phir aage badho") == "Accept karo U P I. Phir aage badho." and say("Sirf 30 sec. Phir 2 min") == "Sirf 30 second. Phir 2 minute."
assert say("approx. 5 log") == "approximately 5 log."
# 10. the word lists are valid, lower case, and every spoken form is plain text the voice can read
sf = json.loads((pathlib.Path(st.__file__).with_name("shortforms.json")).read_text(encoding="utf-8"))
lex = json.loads((pathlib.Path(st.__file__).with_name("pronunciations.json")).read_text(encoding="utf-8"))
assert len(sf) >= 100 and all(k == k.lower() and isinstance(v, str) and v for k, v in sf.items() if not k.startswith("_")), "shortforms.json"
assert {"lovable", "netlify", "dot", "com"} <= set(lex) and all(isinstance(v, str) and v for v in lex.values()), "pronunciations.json"
assert st.SHORT["24/7"] == "twenty four by seven"
print("voice pronounce test passed: 24x7 family, glued units, ordinals/ranges, money, 4K/5G, slashes, web/phone, acronyms, sentence stops")
# 11. end to end: the line the converting model sees (Sarvam) and the text a non-Sarvam engine speaks both carry the fix
import os, tempfile
os.environ["SARVAM_API_KEY"] = "k"
from agent import sarvam, voice
line = "Humari team 24x7 available hai, ₹999 mein website, call 9876543210"
asked = []
sarvam.prepare([line], lambda p: asked.append(p) or {"lines": [{"text": "x", "moods": ["calm"]}]})
assert "twenty four by seven" in asked[0] and "24x7" not in asked[0] and "999 rupees mein" in asked[0] and "9 8 7 6 5, 4 3 2 1 0" in asked[0], asked[0]
seen = []
voice.ENGINES["edge"] = lambda text, mp3, vcfg: (seen.append(text), mp3.write_bytes(b"x"))
voice.media_duration = lambda p: 1.0
voice.synth(line, pathlib.Path(tempfile.mkdtemp()) / "e.mp3", {"voice_engine": "edge", "language": "hi", "voices": {"hi": {"edge": "x"}}}, False)
assert seen == ["Humari team twenty four by seven available hai, 999 rupees mein website, call 9 8 7 6 5, 4 3 2 1 0."], seen
print("end to end: Sarvam prompt and edge voice both get the spoken forms")
