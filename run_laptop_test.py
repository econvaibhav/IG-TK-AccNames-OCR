#!/usr/bin/env python3
"""Run the included short Reel on CPU and open its actual OCR results."""

import argparse
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import sys

from ig_tk_ocr.languages import ListLanguagesAction, resolve_languages

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "examples" / "iltalehti_reel.mp4"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list-languages", action=ListLanguagesAction,
                        help="List codes and presets without loading OCR")
    parser.add_argument("--video", type=Path, default=SAMPLE, help="Optional replacement clip")
    parser.add_argument("--no-open", action="store_true", help="Run the review server without opening a browser")
    parser.add_argument("--no-review", action="store_true", help="Only compute outputs; do not start the review server")
    parser.add_argument("--engine", choices=["easyocr", "paddle"], default="easyocr")
    parser.add_argument("--paddle-size", choices=["tiny", "small", "medium"], default="small")
    parser.add_argument("--lang", nargs="+", default=["en", "pl"], help="Codes/names or europe/europe-latin; see --list-languages")
    parser.add_argument("--layout", choices=["reels", "tiktok", "fixed"], default="reels")
    parser.add_argument("--roi", help="Fixed crop x,y,width,height in the resized 540x960 frame")
    args = parser.parse_args(argv)
    try:
        resolve_languages(args.lang, args.engine)
    except ValueError as exc:
        parser.error(str(exc))
    video = args.video.expanduser().resolve()
    if not video.is_file():
        parser.error(f"Video not found: {video}")
    dependencies = ("cv2", "openpyxl") + (("paddleocr", "paddle") if args.engine == "paddle" else ("easyocr", "torch", "torchvision"))
    missing = [name for name in dependencies
               if importlib.util.find_spec(name) is None]
    if missing:
        print(f"Missing packages: {', '.join(missing)}", file=sys.stderr)
        print("Run bash setup_laptop.sh, then .venv/bin/python run_laptop_test.py", file=sys.stderr)
        return 2

    os.environ.setdefault("OMP_NUM_THREADS", "1" if args.engine == "paddle" else "4")
    os.environ.setdefault("MKL_NUM_THREADS", "4")
    if args.engine == "easyocr":
        import torch
        torch.set_num_threads(min(4, max(1, os.cpu_count() or 1)))

    from ig_tk_ocr.__main__ import main as run_ocr

    destination = ROOT / "results" / datetime.now().strftime("laptop_%Y%m%d_%H%M%S_%f")
    print(f"Video: {video.name}", flush=True)
    print("CPU test: 2 samples/second, stop at 3 matching observations per direction.", flush=True)
    print("At most 12 sampled frames per direction, plus six review time points.", flush=True)
    print(f"Loading {args.engine}. The first run downloads model files.", flush=True)
    command = [
        "run", str(video), "--output", str(destination), "--engine", args.engine, "--paddle-size", args.paddle_size,
        "--lang", *args.lang, "--layout", args.layout, "--sample-fps", "2", "--min-votes", "3",
        "--vote-margin", "0", "--max-samples", "12", "--screenshots", "--excel",
        "--model-dir", str(ROOT / "models"),
    ]
    if args.roi:
        command.extend(["--roi", args.roi])
    code = run_ocr(command)
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
                print("Visible reference in the sample: iltalehti", flush=True)
            if row.get("error"):
                print("Processing error:", row["error"], file=sys.stderr)
    if (destination / "review.html").is_file():
        print(f"\nResults: {destination}", flush=True)
        if not args.no_review:
            from ig_tk_ocr.review import serve
            serve(destination, open_browser=not args.no_open)
    if code:
        print("The run needs attention. Keep the terminal output and the results folder.", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
