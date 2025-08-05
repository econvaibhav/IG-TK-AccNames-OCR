"""Configuration and voting. This module needs only the Python standard library."""

from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
import math
import re


@dataclass(frozen=True)
class Config:
    languages: tuple[str, ...] = ("en", "pl")
    gpu: bool = False
    layout: str = "reels"
    sample_fps: float = 20.0
    min_votes: int = 11
    vote_margin: int = 3
    similarity: float = 0.8
    min_confidence: float = 0.0
    min_duration: float = 0.0
    max_samples: int = 0  # Zero scans the whole clip unless enough votes arrive.
    width: int = 540
    height: int = 960
    circle_roi: tuple[int, int, int, int] = (10, 560, 69, 250)
    crop_size: tuple[int, int] = (380, 40)
    fixed_roi: tuple[int, int, int, int] | None = None

    def __post_init__(self):
        if self.layout not in {"reels", "tiktok", "fixed"}:
            raise ValueError("layout must be reels, tiktok, or fixed")
        if not self.languages or not all(isinstance(x, str) and x for x in self.languages):
            raise ValueError("Provide at least one OCR language code")
        if not math.isfinite(self.sample_fps) or self.sample_fps <= 0:
            raise ValueError("sample_fps must be positive and finite")
        if self.min_votes < 1 or self.vote_margin < 0 or self.max_samples < 0:
            raise ValueError("Invalid vote or sample limits")
        if not 0 <= self.similarity <= 1 or not 0 <= self.min_confidence <= 1:
            raise ValueError("similarity and min_confidence must be between 0 and 1")
        if not math.isfinite(self.min_duration) or self.min_duration < 0:
            raise ValueError("min_duration must be nonnegative and finite")
        if self.width < 1 or self.height < 1:
            raise ValueError("Frame dimensions must be positive")
        if self.layout == "fixed" and self.fixed_roi is None:
            raise ValueError("fixed layout requires --roi x,y,width,height")
        for box in (self.circle_roi, self.fixed_roi):
            if box is not None:
                x, y, w, h = box
                if min(x, y) < 0 or min(w, h) < 1 or x+w > self.width or y+h > self.height:
                    raise ValueError("ROI must fit inside the resized frame")
        if min(self.crop_size) < 1 or self.crop_size[0] > self.width or self.crop_size[1] > self.height:
            raise ValueError("Invalid crop size")


def frame_indices(total_frames, fps, sample_fps, reverse=False, limit=0):
    """Sample at approximately the requested rate, never with a zero step."""
    if total_frames < 1 or not math.isfinite(fps) or fps <= 0:
        raise ValueError("Video has invalid frame count or FPS")
    if not math.isfinite(sample_fps) or sample_fps <= 0 or limit < 0:
        raise ValueError("Invalid sampling options")
    step = max(1, round(fps / sample_fps))
    indices = range(total_frames - 1, -1, -step) if reverse else range(0, total_frames, step)
    return indices[:limit] if limit else indices


def clean_candidates(text, platform="instagram"):
    """Keep plausible labels, preserving uncertain punctuation for human review.

    These are OCR candidates, not verified platform handles. In particular,
    hyphens survive so the software never silently turns one account into another.
    """
    result = []
    for part in re.split(r"\b(?:and|with)\b", text, flags=re.IGNORECASE):
        label = part.strip().lstrip("@").strip()
        label = re.sub(r"\s+(?:Follow|Following)$", "", label, flags=re.IGNORECASE)
        if label.casefold() in {"follow", "following", "see translation", "translation"}:
            continue
        maximum = 30 if platform == "instagram" else 60
        if not 1 <= len(label) <= maximum or label.startswith(".") or label.endswith("."):
            continue
        if platform == "instagram":
            if not re.fullmatch(r"[\w.-]+", label, flags=re.UNICODE):
                continue
        elif not re.fullmatch(r"[\w. '\-]+", label, flags=re.UNICODE):
            continue
        if re.fullmatch(r"[\d,.]+", label):
            continue
        if label.casefold() not in {x.casefold() for x in result}:
            result.append(label)
    return result


def handle_like(label):
    """Conservative syntax check only; never a claim that an account exists."""
    return bool(re.fullmatch(r"[A-Za-z0-9_](?:[A-Za-z0-9_.]{0,28}[A-Za-z0-9_])?", label)) and ".." not in label


class Votes:
    def __init__(self):
        self.counts = Counter()
        self.spelling = {}

    def add_frame(self, candidates):
        # Duplicate boxes or substring matches must not add extra votes in one frame.
        for label in candidates:
            self.spelling.setdefault(label.casefold(), label)
        self.counts.update({x.casefold() for x in candidates})

    def top(self, margin=3):
        if not self.counts:
            return []
        best = max(self.counts.values())
        return [
            {"name": self.spelling[name], "votes": count}
            for name, count in sorted(self.counts.items(), key=lambda p: (-p[1], p[0]))
            if best - count <= margin
        ]


def compare_passes(forward, reverse, threshold=0.8):
    """One-to-one, highest-similarity-first pairing of candidate labels."""
    left = [x["name"] for x in forward]
    right = [x["name"] for x in reverse]
    # Letter-case differences alone should not create a second account candidate.
    union_by_key = {}
    for label in left + right:
        union_by_key.setdefault(label.casefold(), label)
    union = list(union_by_key.values())
    possibilities = sorted(
        [(SequenceMatcher(None, a.casefold(), b.casefold()).ratio(), i, j)
         for i, a in enumerate(left) for j, b in enumerate(right)],
        key=lambda p: (-p[0], p[1], p[2]),
    )
    used_left, used_right, matches = set(), set(), []
    for score, i, j in possibilities:
        if score >= threshold and i not in used_left and j not in used_right:
            matches.append({"forward": left[i], "reverse": right[j], "similarity": round(score, 4)})
            used_left.add(i)
            used_right.add(j)
    if not left and not right:
        status = "no_text"
    elif not left or not right:
        status = "one_sided"
    elif len(matches) < max(len(left), len(right)):
        status = "disagreement"
    elif all(m["forward"].casefold() == m["reverse"].casefold() for m in matches):
        status = "agreement"
    else:
        status = "similar"
    return {"status": status, "union_names": union, "matches": matches}
