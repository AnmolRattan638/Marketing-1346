import os
import shutil
import subprocess
import tempfile
import unittest

from viralsim import video

HAVE = shutil.which("ffmpeg") is not None


@unittest.skipUnless(HAVE, "ffmpeg missing")
class VideoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.dyn, cls.still = os.path.join(cls.d, "dyn.mp4"), os.path.join(cls.d, "still.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=270x480:r=24:d=10", "-f", "lavfi", "-i", "sine=f=300:d=10",
                        "-shortest", "-pix_fmt", "yuv420p", cls.dyn], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x444444:s=270x480:r=24:d=10", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                        "-shortest", "-pix_fmt", "yuv420p", cls.still], check=True)

    def test_measure(self):
        m = video.measure(self.dyn)
        self.assertEqual(m["seconds"], 10)
        self.assertGreater(m["motion"].mean(), 0.3)
        self.assertTrue(m["voiced"].all())

    def test_lively_beats_static(self):
        a, b = video.analyze_video(self.dyn), video.analyze_video(self.still)
        self.assertGreater(a["score"], b["score"] + 20)
        self.assertFalse(b["worth_posting"])
        kinds = [w["kind"] for w in b["weak_points"]]
        self.assertIn("static_stretch", kinds)
        self.assertEqual(kinds.count("dead_air"), 1)

    def test_weak_points_name_scenes_and_feedback(self):
        spans = [{"id": "s1", "beat": "pain", "start": 0, "end": 5}, {"id": "s2", "beat": "fix", "start": 5, "end": 10}]
        r = video.analyze_video(self.still, spans)
        self.assertTrue(any(w["scene"] == "s1" for w in r["weak_points"]))
        fb = video.feedback(r)
        self.assertIn("RETENTION REPORT", fb)
        self.assertIn("FIX:", fb)
        self.assertEqual(len(r["bots"]), 6)

    def test_deterministic(self):
        self.assertEqual(video.analyze_video(self.still)["score"], video.analyze_video(self.still)["score"])


if __name__ == "__main__":
    unittest.main()
