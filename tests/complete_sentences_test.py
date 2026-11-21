import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.agents import scriptwriter as sw

BROKEN = [
    "Prateeksha ke mutabik, over 75% Indians mobile se browse karte; 3 sec se zyada load ho to site zyadatar visitors chhod.",
    "Mobile-first, tez load, kyunki customers ek tap se call ya WhatsApp kar sakte hain.",
    "PageSurgeon ke hisaab se homepage pe 5 second batana hai ki aap kya karte hain.",
]
FINE = [
    "Raat ko customer message karta hai aur koi jawab nahi deta.",
    "Pehle chatbot WhatsApp pe lagao, kyunki isse raat ke message miss nahi hote.",
    "Comment SITE likho, tumhe simple website checklist mil sakti hai.",
    "Google par pehle 3 second mein site load ho to log rukte hain.",
    "Aapki site pe 5 second mein pata chalna chahiye ki aap kya karte hain.",
    "Website na hona hi wajah hai ki customers aapko dhundh nahi paate.",
]


def test_broken_lines_are_flagged():
    for line in BROKEN:
        assert sw.grammar_problems(line), line


def test_complete_lines_are_not_flagged():
    for line in FINE:
        assert not sw.grammar_problems(line), (line, sw.grammar_problems(line))


def test_autofix_adds_helper():
    assert sw.autofix_endings("Log mobile se browse karte;") == "Log mobile se browse karte hain."
    assert sw.autofix_endings("Wo roz check karta") == "Wo roz check karta hai."
    assert sw.autofix_endings("Wo check nahi karta") == "Wo check nahi karta"


def test_grammar_is_repairable_not_fatal():
    assert sw.is_soft("pain: grammar: sentence stops mid-thought")
    assert sw.WORDS[1] >= 26 and sw.TOTAL_WORDS[1] >= 92


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("ok")
