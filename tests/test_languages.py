import builtins
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from instagram_ocr.__main__ import main
from instagram_ocr.core import Config
from instagram_ocr.engines import paddle_recognizers
from instagram_ocr.languages import (EUROPE_LANGUAGES, LANGUAGE_PRESETS,
    expand_languages, resolve_languages)
from instagram_ocr.vision import make_reader
import run_laptop_test


class LanguageCatalogTests(unittest.TestCase):
    def test_requested_languages_and_europe_models(self):
        required = {"en", "bg", "hr", "fr", "hu", "fi", "sv", "de", "pl", "es", "pt"}
        self.assertTrue(required <= set(EUROPE_LANGUAGES))
        self.assertEqual(len(EUROPE_LANGUAGES), 32)
        self.assertEqual(len(LANGUAGE_PRESETS["europe-latin"]), 27)
        self.assertEqual(paddle_recognizers(("europe",)), [
            "PP-OCRv6_small_rec", "cyrillic_PP-OCRv5_mobile_rec", "el_PP-OCRv5_mobile_rec"])
        self.assertEqual(paddle_recognizers(("europe-latin",)), ["PP-OCRv6_small_rec"])
        self.assertEqual(Config().languages, ("en", "pl"))

    def test_aliases_order_deduplication_and_unambiguous_script_codes(self):
        self.assertEqual(expand_languages(["English", "Bulgaria", "BG", "Croatia,France", "Sweden", "German"]),
                         ("en", "bg", "hr", "fr", "sv", "de"))
        self.assertEqual(expand_languages(["Czech Republic", "Slovenian", "GR", "si", "se"]),
                         ("cs", "sl", "el", "sv"))
        self.assertEqual(expand_languages(["uk", "eu", "serbian_latin", "serbian_cyrillic"]),
                         ("uk", "eu", "rs_latin", "rs_cyrillic"))
        self.assertEqual(expand_languages(["en", "europe", "French"]), EUROPE_LANGUAGES)
        for invalid in ([], [""], ["en,,pl"], [None]):
            with self.assertRaises(ValueError):
                expand_languages(invalid)
        with self.assertRaisesRegex(ValueError, "Unsupported Paddle"):
            resolve_languages(["serbian"], "paddle")

    def test_easyocr_failure_is_early_and_does_not_switch_engine(self):
        with patch("builtins.__import__", side_effect=AssertionError("OCR must not be imported")):
            with self.assertRaisesRegex(ValueError, "--engine paddle"):
                make_reader(Config(languages=EUROPE_LANGUAGES), engine="easyocr")
        for languages in (["europe"], ["europe-latin"], ["en", "fi"], ["en", "el"], ["en", "de", "bg"]):
            with self.assertRaisesRegex(ValueError, "--engine paddle"):
                resolve_languages(languages, "easyocr")
        self.assertEqual(resolve_languages(["en", "bg"], "easyocr"), ("en", "bg"))
        self.assertEqual(resolve_languages(["en", "de", "pl"], "easyocr"), ("en", "de", "pl"))
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(["run", "does-not-exist", "--output", "unused", "--lang", "europe"])
        self.assertEqual(code, 2)
        self.assertIn("--engine paddle", stderr.getvalue())
        self.assertNotIn("No supported video", stderr.getvalue())

    def test_catalog_needs_neither_video_arguments_nor_ocr_imports(self):
        real_import = builtins.__import__
        def forbid_models(name, *args, **kwargs):
            if name.split(".")[0] in {"cv2", "easyocr", "torch", "paddleocr", "paddle"}:
                raise AssertionError("language listing imported " + name)
            return real_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=forbid_models):
            for entry, argv in [(main, ["--list-languages"]),
                                (main, ["run", "--list-languages"]),
                                (main, ["batch", "--list-languages"]),
                                (run_laptop_test.main, ["--list-languages"])]:
                output = io.StringIO()
                with redirect_stdout(output), self.assertRaises(SystemExit) as end:
                    entry(argv)
                self.assertEqual(end.exception.code, 0)
                self.assertIn("Bulgarian", output.getvalue())
                self.assertIn("Finnish", output.getvalue())
                self.assertIn("europe-latin", output.getvalue())

    def test_run_and_batch_record_preset_and_resolved_languages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clip = root / "part_1_reel.mp4"
            clip.touch()
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps([str(root)]))
            for mode in ("run", "batch"):
                output = root / mode
                def fake_video(path, reader, config, screenshot_root):
                    return {"path": str(path), "status": "no_text", "union_names": []}
                with patch("instagram_ocr.__main__.make_reader", return_value=SimpleNamespace(model_names=["test"])) as reader, \
                     patch("instagram_ocr.__main__.process_video", side_effect=fake_video), \
                     redirect_stdout(io.StringIO()):
                    command = (["run", str(clip)] if mode == "run" else
                               ["batch", str(manifest), "--task-id", "1"])
                    code = main(command + ["--output", str(output), "--engine", "paddle", "--lang", "europe"])
                self.assertEqual(code, 0)
                self.assertEqual(reader.call_args.args[0].languages, EUROPE_LANGUAGES)
                folder = output if mode == "run" else output / "task_00001"
                metadata = json.loads((folder / "run.json").read_text())
                self.assertEqual(metadata["requested_languages"], ["europe"])
                self.assertEqual(metadata["config"]["languages"], list(EUROPE_LANGUAGES))


if __name__ == "__main__":
    unittest.main()
