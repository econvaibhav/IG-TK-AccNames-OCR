"""Portable file discovery, manifests and review exports."""

import csv
import json
from pathlib import Path
import re

VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".m4v", ".webm"}


def natural_key(path):
    return tuple((1, int(x)) if x.isdigit() else (0, x.casefold()) for x in re.split(r"(\d+)", str(path)))


def discover_videos(path, recursive=False):
    path = Path(path)
    if path.is_file():
        return [path] if path.suffix.lower() in VIDEO_SUFFIXES else []
    if not path.is_dir():
        raise ValueError(f"Input does not exist: {path}")
    candidates = path.rglob("*") if recursive else path.iterdir()
    return sorted((p for p in candidates if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES), key=natural_key)


def platform_from_path(path):
    parts = re.split(r"[/\\]+", str(path).casefold())
    if "instagram" in parts:
        return "instagram"
    if "tiktok" in parts:
        return "tiktok"
    return None


def make_manifest(root):
    # Include folders containing videos even when they also contain subfolders.
    return sorted({str(p.parent.resolve()) for p in discover_videos(root, recursive=True)}, key=natural_key)


def pick_task(manifest, task_id):
    if not isinstance(manifest, list) or not all(isinstance(x, str) for x in manifest):
        raise ValueError("Manifest must be a JSON list of folder paths")
    if not 1 <= task_id <= len(manifest):
        raise ValueError(f"Task ID must be 1..{len(manifest)} (one-based)")
    return Path(manifest[task_id - 1])


def csv_row(result):
    encode = lambda value: json.dumps(value, ensure_ascii=False)
    return {
        "path": result["path"], "status": result["status"],
        "needs_review": result.get("needs_review", True),
        "review_reasons": encode(result.get("review_reasons", [])),
        "forward_names": encode(result.get("forward", {}).get("candidates", [])),
        "reverse_names": encode(result.get("reverse", {}).get("candidates", [])),
        "union_names": encode(result.get("union_names", [])),
        "matches": encode(result.get("matches", [])),
        "duration_seconds": result.get("duration_seconds", ""),
        "error": result.get("error", ""),
    }


def save_csv(results, path):
    rows = [csv_row(r) for r in results]
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]) if rows else list(csv_row({"path":"", "status":""})))
        writer.writeheader()
        writer.writerows(rows)


def save_review(results, path):
    from .review_page import save_review as render
    render(results, path)
