#!/usr/bin/env python3
"""Run the included short Reel on CPU and open its actual OCR results."""

import argparse
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import sys
import webbrowser

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "examples" / "part_16_reel.mp4"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=SAMPLE, help="Optional replacement clip")
    parser.add_argument("--no-open", action="store_true", help="Print the HTML path without opening it")
    args = parser.parse_args(argv)
    video = args.video.expanduser().resolve()
    if not video.is_file():
        parser.error(f"Video not found: {video}")
    missing = [name for name in ("cv2", "easyocr", "torch", "torchvision", "openpyxl")
               if importlib.util.find_spec(name) is None]
    if missing:
        print(f"Missing packages: {', '.join(missing)}", file=sys.stderr)
        print("Run bash setup_laptop.sh, then .venv/bin/python run_laptop_test.py", file=sys.stderr)
        return 2

    os.environ.setdefault("OMP_NUM_THREADS", "4")
    os.environ.setdefault("MKL_NUM_THREADS", "4")
    import torch
    torch.set_num_threads(min(4, max(1, os.cpu_count() or 1)))

    from instagram_ocr.__main__ import main as run_ocr

    destination = ROOT / "results" / datetime.now().strftime("laptop_%Y%m%d_%H%M%S_%f")
    print(f"Video: {video.name}", flush=True)
    print("CPU test: 2 samples/second, stop at 3 matching observations per direction.", flush=True)
    print("At most 12 sampled frames per direction, plus three review screenshots.", flush=True)
    print("Loading EasyOCR. Its first run downloads the detection and recognition models.", flush=True)
    code = run_ocr([
        "run", str(video), "--output", str(destination),
        "--lang", "en", "pl", "--sample-fps", "2", "--min-votes", "3",
        "--vote-margin", "0", "--max-samples", "12", "--screenshots", "--excel",
        "--model-dir", str(ROOT / "models"),
    ])
    details = destination / "details.jsonl"
    if details.is_file():
        rows = [json.loads(line) for line in details.read_text(encoding="utf-8").splitlines() if line.strip()]
        if rows:
            row = rows[0]
            print("\nCandidates:", ", ".join(row.get("union_names", [])) or "none", flush=True)
            print("Comparison:", row["status"], flush=True)
            for direction in ("forward", "reverse"):
                candidates = row.get(direction, {}).get("candidates", [])
                readings = ", ".join(f"{c['name']} ({c['votes']} frames)" for c in candidates) or "none"
                print(f"{direction.title()}: {readings}", flush=True)
            if video == SAMPLE.resolve():
                # A human-read reference for checking this sample. Never used as OCR input.
                print("Visible reference in the sample: thestoryofourhome.pl", flush=True)
            if row.get("error"):
                print("Processing error:", row["error"], file=sys.stderr)
    report = destination / "review.html"
    if report.is_file():
        print(f"\nOpen the result: {report}", flush=True)
        print(f"Excel: {destination / 'results.xlsx'}", flush=True)
        if not args.no_open:
            try:
                webbrowser.open(report.as_uri())
            except Exception:
                pass  # The path above is sufficient if no desktop browser is available.
    if code:
        print("The run needs attention. Keep the terminal output and the results folder.", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

