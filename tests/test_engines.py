import unittest
from types import SimpleNamespace

from instagram_ocr.core import Votes, clean_candidates
from instagram_ocr.engines import PaddleReader, paddle_recognizers
from instagram_ocr.__main__ import parser


class LanguageTests(unittest.TestCase):
    def test_default_remains_v6_and_bulgarian_uses_cyrillic(self):
        self.assertEqual(paddle_recognizers(("en", "pl")), ["PP-OCRv6_small_rec"])
        self.assertEqual(paddle_recognizers(("en", "bg")), ["cyrillic_PP-OCRv5_mobile_rec"])
        self.assertEqual(paddle_recognizers(("en", "de", "pl", "bg")),
                         ["PP-OCRv6_small_rec", "cyrillic_PP-OCRv5_mobile_rec"])
        self.assertEqual(paddle_recognizers(("en", "el")), ["el_PP-OCRv5_mobile_rec"])
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            paddle_recognizers(("en", "unknown"))
        with self.assertRaisesRegex(ValueError, "Japanese"):
            paddle_recognizers(("ja",), "tiny")

    def test_mixed_scripts_keep_conflicts_but_cannot_double_votes(self):
        first_box = [[0, 0], [80, 0], [80, 30], [0, 30]]
        other_box = [[100, 0], [180, 0], [180, 30], [100, 30]]
        def model(texts, boxes):
            return SimpleNamespace(predict=lambda image: [{"rec_texts": texts,
                "rec_scores": [.9] * len(texts), "rec_polys": boxes}])
        reader = PaddleReader.__new__(PaddleReader)
        reader.recognition_models = ["latin", "cyrillic"]
        reader.models = [model(["news", "Nova"], [first_box, other_box]),
                         model(["news", "Нова", "news"], [first_box, other_box, other_box])]
        readings = reader.readtext(None)
        self.assertEqual([text for _, text, _ in readings], ["news", "Nova", "Нова", "news"])
        self.assertEqual(reader.last_detection_models, [["latin", "cyrillic"], ["latin"], ["cyrillic"], ["cyrillic"]])
        votes = Votes()
        votes.add_frame([text for _, text, _ in readings])
        self.assertEqual(votes.counts, {"news": 1, "nova": 1, "нова": 1})
        self.assertEqual(clean_candidates("Новини България", "tiktok"), ["Новини България"])

    def test_cli_preserves_requested_language_set(self):
        args = parser().parse_args(["run", "clips", "--output", "results", "--engine", "paddle",
                                   "--lang", "en", "de", "pl", "bg"])
        self.assertEqual(args.lang, ["en", "de", "pl", "bg"])


if __name__ == "__main__":
    unittest.main()
