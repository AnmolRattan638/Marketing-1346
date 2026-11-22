import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video-agent"))
from src.agents import scriptwriter as sw
from agent import speech_text as st
cases = {
    "Kya aapki dukaan raat ko bhi customer lose karti hai?": "Kya aapka business raat ko bhi customer lose karti hai?",
    "Bohot kam dukaan wale ye karte hain.": "Bohot kam business owners ye karte hain.",
    "Customer dusri dukaan chala jaata hai.": "Customer dusra business chala jaata hai.",
    "Raat 11 baje dukaan band hai.": "Raat 11 baje business band hai.",
    "Kaash mujhe apni dukaan ki website ka pata hota.": "Kaash mujhe apne business ki website ka pata hota.",
}
for a, b in cases.items():
    assert sw.businessify(a) == b, (sw.businessify(a), b)
    assert "dukaan" not in st.untranslate(a).lower() and "dukan" not in st.untranslate(a).lower(), st.untranslate(a)
assert st.untranslate("आपकी दुकान और दुकानदारों") == "आपकी बिज़नेस और बिज़नेस ओनर्स"
assert "dukaan" not in open("config/hooks.json").read().lower()
print("business word ok")
