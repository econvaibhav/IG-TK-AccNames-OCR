"""Exercise failure/cleanup paths without downloading the EasyOCR models."""

from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from ig_tk_ocr.core import Config
from ig_tk_ocr.files import save_csv, save_review
from ig_tk_ocr.pipeline import process_video, scan
from ig_tk_ocr.vision import open_video


class Capture:
    def __init__(self, readable=True):
        self.readable, self.released = readable, False

    def isOpened(self): return True
    def get(self, key): return 10
    def set(self, *args): pass
    def read(self): return self.readable, object()
    def release(self): self.released = True


class PipelineTests(unittest.TestCase):
    def test_no_circle_never_accesses_undefined_results(self):
        with patch("ig_tk_ocr.pipeline.cv_module", return_value=SimpleNamespace(CAP_PROP_POS_FRAMES=1)), \
             patch("ig_tk_ocr.pipeline.crop_frame", return_value=(object(), None, None)):
            result = scan(Capture(), 5, 4, None, Config())
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["crops_found"], 0)

    def test_capture_released_even_when_processing_raises(self):
        cap = Capture()
        cv = SimpleNamespace(VideoCapture=lambda path: cap, CAP_PROP_FPS=1, CAP_PROP_FRAME_COUNT=2)
        with patch("ig_tk_ocr.vision.cv_module", return_value=cv):
            with self.assertRaises(RuntimeError):
                with open_video("test.mp4"):
                    raise RuntimeError("OCR failed")
        self.assertTrue(cap.released)

    def test_early_exit_counts_frames_once_and_keeps_raw_text(self):
        reader = SimpleNamespace(readtext=lambda *a, **k: [(None,"alpha",0.9),(None,"alpha",0.8)])
        with patch("ig_tk_ocr.pipeline.cv_module", return_value=SimpleNamespace(CAP_PROP_POS_FRAMES=1)), \
             patch("ig_tk_ocr.pipeline.crop_frame", return_value=(None, object(), (1,2,3,4))):
            result = scan(Capture(), 10, 100, reader, Config(min_votes=3))
        self.assertEqual(result["frames_attempted"], 3)
        self.assertEqual(result["candidates"], [{"name":"alpha", "votes":3}])
        self.assertEqual(len(result["observations"]), 6)
        self.assertTrue(result["enough_votes"])

    def test_all_decode_failures_are_explicit(self):
        with patch("ig_tk_ocr.pipeline.cv_module", return_value=SimpleNamespace(CAP_PROP_POS_FRAMES=1)):
            result = scan(Capture(False), 10, 4, None, Config())
        self.assertEqual(result["decode_failures"], 4)
        self.assertFalse(result["enough_votes"])

    def test_matching_nonstandard_readings_still_need_review(self):
        @contextmanager
        def video(path): yield Capture(), 10, 100
        data = {"candidates":[{"name":"name-with-hyphen", "votes":11}],
                "enough_votes":True, "decode_failures":0}
        with patch("ig_tk_ocr.pipeline.open_video", video), patch("ig_tk_ocr.pipeline.scan", return_value=data):
            result = process_video("a.mp4", None, Config())
        self.assertEqual(result["status"], "agreement")
        self.assertTrue(result["needs_review"])
        self.assertIn("nonstandard_label", result["review_reasons"])

    def test_csv_and_html_escape_ocr_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            row = {"path":"<script>.mp4", "status":"no_text", "union_names":["a,b", 'x"y']}
            save_csv([row], path / "results.csv")
            save_review([row], path / "review.html")
            import csv
            with (path / "results.csv").open() as stream:
                saved = next(csv.DictReader(stream))
            self.assertEqual(json.loads(saved["union_names"]), row["union_names"])
            text = (path / "review.html").read_text()
            self.assertNotIn("<script>", text)
            self.assertIn("&lt;script&gt;", text)


if __name__ == "__main__":
    unittest.main()
