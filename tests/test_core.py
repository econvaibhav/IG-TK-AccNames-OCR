import tempfile
from pathlib import Path
import unittest

from instagram_ocr.core import Config, Votes, clean_candidates, compare_passes, frame_indices, handle_like
from instagram_ocr.files import discover_videos, make_manifest, pick_task, platform_from_path


class SamplingTests(unittest.TestCase):
    def test_low_fps_short_video_never_has_zero_step(self):
        self.assertEqual(list(frame_indices(3, 5, 20)), [0, 1, 2])
        self.assertEqual(list(frame_indices(3, 5, 20, reverse=True)), [2, 1, 0])

    def test_invalid_metadata_and_settings(self):
        for fps in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                frame_indices(10, fps, 3)
        with self.assertRaises(ValueError):
            Config(sample_fps=0)
        with self.assertRaises(ValueError):
            Config(layout="fixed")
        with self.assertRaises(ValueError):
            Config(fixed_roi=(0, 900, 200, 80))

    def test_sample_limit(self):
        self.assertEqual(list(frame_indices(60, 30, 10, limit=3)), [0, 3, 6])


class VotingTests(unittest.TestCase):
    def test_duplicate_boxes_and_substrings_do_not_inflate_votes(self):
        votes = Votes()
        votes.add_frame(["news", "news", "newsroom"])
        votes.add_frame(["news"])
        self.assertEqual(votes.counts, {"news": 2, "newsroom": 1})

    def test_margin_is_measured_from_winner_not_neighbor(self):
        votes = Votes()
        for i in range(10):
            votes.add_frame(["alpha"] + (["beta"] if i < 7 else []) + (["gamma"] if i < 4 else []))
        self.assertEqual([x["name"] for x in votes.top(3)], ["alpha", "beta"])

    def test_split_before_validation_and_preserve_uncertainty(self):
        self.assertEqual(clean_candidates("@alpha and beta Follow"), ["alpha", "beta"])
        self.assertEqual(clean_candidates("folklore"), ["folklore"])
        self.assertEqual(clean_candidates("thestoryofourhome-pl"), ["thestoryofourhome-pl"])
        self.assertFalse(handle_like("thestoryofourhome-pl"))
        self.assertEqual(clean_candidates("VPN connected"), [])
        self.assertEqual(clean_candidates("Follow"), [])
        self.assertEqual(clean_candidates("1,000"), [])

    def test_agreement_is_not_merely_two_nonempty_passes(self):
        left = [{"name": "alpha", "votes": 11}]
        self.assertEqual(compare_passes(left, [{"name":"zzzzz", "votes":11}])["status"], "disagreement")
        self.assertEqual(compare_passes(left, left)["status"], "agreement")
        self.assertEqual(compare_passes(left, [])["status"], "one_sided")
        self.assertEqual(compare_passes([], [])["status"], "no_text")

    def test_similar_labels_remain_visible(self):
        result = compare_passes([{"name":"city.stories"}], [{"name":"city_stories"}])
        self.assertEqual(result["status"], "similar")
        self.assertEqual(result["union_names"], ["city.stories", "city_stories"])

    def test_case_difference_does_not_create_multiple_accounts(self):
        result = compare_passes([{"name":"City.Stories"}], [{"name":"city.stories"}])
        self.assertEqual(result["status"], "agreement")
        self.assertEqual(result["union_names"], ["City.Stories"])


class FileTests(unittest.TestCase):
    def test_platform_paths_cross_operating_systems(self):
        self.assertEqual(platform_from_path(r"C:\data\TiKToK\part_1.mp4"), "tiktok")
        self.assertEqual(platform_from_path("/data/Instagram/a.mp4"), "instagram")
        self.assertIsNone(platform_from_path("/data/my_instagram/a.mp4"))

    def test_nonleaf_folders_uppercase_suffix_and_numeric_sort(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "child").mkdir()
            for name in ("part_10.MP4", "part_2.mp4", "child/a.mov"):
                (root / name).touch()
            self.assertEqual([p.name for p in discover_videos(root)], ["part_2.mp4", "part_10.MP4"])
            self.assertEqual(set(make_manifest(root)), {str(root), str(root / "child")})

    def test_one_based_slurm_range(self):
        self.assertEqual(pick_task(["a", "b"], 1), Path("a"))
        for index in (-1, 0, 3):
            with self.assertRaises(ValueError):
                pick_task(["a", "b"], index)


if __name__ == "__main__":
    unittest.main()
