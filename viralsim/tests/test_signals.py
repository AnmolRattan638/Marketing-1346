"""Tests for the original signal engine (signals.py): ordering, each rule, the insight contract, the account effect, and safe edge cases."""
import unittest

from viralsim.creator import Creator
from viralsim.signals import analyze_text, predict_signals

GREAT = "Why do customers ghost your page?\n\u2192 3 details they check first\n\u2192 Where you are\n\u2192 How to reach you\nDM SITE for a quick look. #SmallBusinessIndia"
PLAIN = "We build websites for small businesses."
BAD = "LIMITED OFFER!!! 100% guaranteed best price, act now! Tag a friend and like and share https://x.co/a #a #b #c #d #e #f #g #h"
sc = lambda t, c=None, **m: predict_signals(analyze_text(t, **m), c)


class SignalTests(unittest.TestCase):
    def test_ordering_and_spread(self):
        great, plain, bad = sc(GREAT, has_image=True).score, sc(PLAIN).score, sc(BAD).score
        self.assertGreater(great, plain)
        self.assertGreater(plain, bad)
        self.assertGreater(great - bad, 40, "the score must actually spread out")
        for s in (great, plain, bad):
            self.assertTrue(0 <= s <= 100)

    def test_features(self):
        f = analyze_text("**\U0001d5e0\U0001d5dc\U0001d5e6\U0001d5e7\U0001d5dc**: 3 tips? #a #b @x https://x.co/a \u2705!!")
        self.assertTrue(f.has_question and f.has_number and f.links == 1 and f.hashtags == 2 and f.mentions == 1 and f.emojis >= 1 and f.exclamations == 2)
        self.assertTrue(analyze_text("Why 3 mistakes cost you customers").has_hook)
        self.assertFalse(analyze_text("We would like to tell you about a thing that we do for people in towns").has_hook)
        self.assertEqual(analyze_text("").words, 0)
        f = analyze_text("a", has_video=True, is_thread=True, thread_length=4)
        self.assertTrue(f.has_video and f.is_thread and f.thread_length == 4)

    def test_each_rule_moves_the_right_number(self):
        base = "Here is what I learned shipping a product."
        self.assertGreater(sc(base + " What would you add?").probs["reply"], sc(base).probs["reply"])
        self.assertGreater(sc(base).score, sc(base + " https://x.co/a").score)
        self.assertGreater(sc(base, has_image=True).probs["dwell"], sc(base).probs["dwell"])
        self.assertGreater(sc(base + " Tag a friend!").risks["report"], sc(base).risks["report"])
        self.assertGreater(sc(base + " 100% guaranteed").risks["not_interested"], sc(base).risks["not_interested"])
        self.assertGreater(sc("Myth: more posts means more clients. Fact: clearer posts do.").probs["reply"], sc("More posts means more clients.").probs["reply"])
        self.assertGreater(sc(GREAT).probs["bookmark"], sc(PLAIN).probs["bookmark"])
        self.assertLess(sc(base + " " + " ".join(f"#t{i}" for i in range(9))).probs["favorite"], sc(base).probs["favorite"])

    def test_insight_contract(self):
        ins = sc(BAD).insights
        self.assertTrue(ins)
        for i in ins:
            self.assertEqual(set(i), {"type", "title", "description", "impact"})
            self.assertIn(i["type"], ("positive", "negative", "warning", "neutral"))
            self.assertIn(i["impact"], ("high", "medium", "low"))
        self.assertEqual([i["impact"] for i in ins], sorted((i["impact"] for i in ins), key=("high", "medium", "low").index), "high impact first")
        titles = {i["title"] for i in ins}
        self.assertTrue({"Link inside the text", "Engagement-bait wording", "Hype or guarantee words", "Too many hashtags"} <= titles, titles)
        self.assertIn("Strong opening line", {i["title"] for i in sc(GREAT, has_image=True).insights})
        self.assertFalse([i for i in sc(GREAT, has_image=True).insights if i["type"] == "negative"], "a clean post gets no negative tip")

    def test_account_effect_and_expected_counts(self):
        small, big = Creator(followers=10), Creator(followers=100000, avg_engagement_rate=4.0, verified=True)
        a, b = sc(GREAT, small, has_image=True), sc(GREAT, big, has_image=True)
        self.assertGreater(b.probs["favorite"], a.probs["favorite"])
        self.assertGreater(b.expected["views"], a.expected["views"] * 1000)
        self.assertEqual(set(a.expected), {"views", "likes", "reposts", "replies", "bookmarks"})
        self.assertTrue(all(0 <= v <= 0.95 for v in {**a.probs, **a.risks}.values()))

    def test_safe_on_odd_input(self):
        for t in ("", "   ", "!!!???", "#", "\u2705" * 50, "A" * 5000):
            p = sc(t)
            self.assertTrue(0 <= p.score <= 100 and isinstance(p.insights, list))


if __name__ == "__main__":
    unittest.main()
