"""Command line: ig-tk-accnames-ocr --help (or python -m ig_tk_ocr)."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import sys

from . import __version__
from .core import Config
from .files import discover_videos, make_manifest, pick_task, platform_from_path, save_csv, save_review
from .pipeline import process_video
from .languages import ListLanguagesAction, resolve_languages
from .vision import make_reader, open_video


def roi_arg(value):
    try:
        box = tuple(int(x) for x in value.split(","))
        if len(box) != 4:
            raise ValueError
        return box
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ROI must be x,y,width,height") from exc


def parser():
    p = argparse.ArgumentParser(prog="ig-tk-accnames-ocr",
                                description="IG-TK-AccNames-OCR: read account labels from social-media clips.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--list-languages", action=ListLanguagesAction,
                   help="List language codes and presets without loading OCR")
    commands = p.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="Process a video or folder")
    run.add_argument("input", type=Path)
    batch = commands.add_parser("batch", help="Process one folder from a Slurm manifest")
    batch.add_argument("manifest", type=Path)
    batch.add_argument("--task-id", type=int, help="One-based; defaults to SLURM_ARRAY_TASK_ID")
    for cmd in (run, batch):
        cmd.add_argument("--list-languages", action=ListLanguagesAction,
                         help="List language codes and presets without loading OCR")
        cmd.add_argument("--output", type=Path, required=True, help="New output directory")
        cmd.add_argument("--recursive", action="store_true")
        cmd.add_argument("--layout", choices=["reels", "tiktok", "fixed", "auto"], default="reels")
        cmd.add_argument("--roi", type=roi_arg, help="Fixed ROI in the resized 540x960 frame")
        cmd.add_argument("--circle-roi", type=roi_arg, default=(10, 560, 69, 250))
        cmd.add_argument("--lang", nargs="+", default=["en", "pl"],
                         help="Codes/names or europe/europe-latin, e.g. en de pl bg. See --list-languages.")
        cmd.add_argument("--engine", choices=["easyocr", "paddle"], default="easyocr")
        cmd.add_argument("--paddle-size", choices=["tiny", "small", "medium"], default="small")
        cmd.add_argument("--gpu", action="store_true")
        cmd.add_argument("--sample-fps", type=float, default=20)
        cmd.add_argument("--min-votes", type=int, default=11)
        cmd.add_argument("--vote-margin", type=int, default=3)
        cmd.add_argument("--similarity", type=float, default=0.8)
        cmd.add_argument("--min-confidence", type=float, default=0)
        cmd.add_argument("--min-duration", type=float, default=0)
        cmd.add_argument("--max-samples", type=int, default=0)
        cmd.add_argument("--screenshots", action="store_true")
        cmd.add_argument("--excel", action="store_true", help="Also save an Excel review workbook")
        cmd.add_argument("--model-dir", type=Path)
        cmd.add_argument("--offline", action="store_true", help="Require local OCR model files")
    review = commands.add_parser("review", help="Open saved results in an editable local review")
    review.add_argument("folder", type=Path)
    review.add_argument("--port", type=int, default=0, help="0 chooses a free local port")
    review.add_argument("--no-open", action="store_true")
    manifest = commands.add_parser("manifest", help="List all folders containing video files")
    manifest.add_argument("input", type=Path)
    manifest.add_argument("--output", type=Path, required=True)
    duration = commands.add_parser("duration", help="Total durations, replacing spaintime.py")
    duration.add_argument("input", type=Path)
    return p


def run(args):
    languages = resolve_languages(args.lang, args.engine)
    if args.command == "batch":
        task = args.task_id
        if task is None:
            raw = os.getenv("SLURM_ARRAY_TASK_ID")
            if raw is None:
                raise ValueError("Provide --task-id or SLURM_ARRAY_TASK_ID")
            task = int(raw)
        source = pick_task(json.loads(args.manifest.read_text(encoding="utf-8")), task)
        destination = args.output / f"task_{task:05d}"
    else:
        source, destination = args.input, args.output
    if args.roi is not None and args.layout not in {"fixed", "tiktok"}:
        raise ValueError("--roi requires --layout fixed or tiktok")
    config = Config(
        languages=languages, gpu=args.gpu,
        layout="reels" if args.layout == "auto" else args.layout,
        sample_fps=args.sample_fps, min_votes=args.min_votes,
        vote_margin=args.vote_margin, similarity=args.similarity,
        min_confidence=args.min_confidence, min_duration=args.min_duration,
        max_samples=args.max_samples, circle_roi=args.circle_roi, fixed_roi=args.roi,
    )
    videos = discover_videos(source, args.recursive)
    if not videos:
        raise ValueError("No supported video files found")
    if destination.exists():
        raise ValueError(f"Output already exists; choose a new directory: {destination}")
    if args.excel:
        try:
            import openpyxl  # noqa: F401
        except ImportError as exc:
            raise RuntimeError('Excel export needs: python -m pip install ".[excel]"') from exc
    # Initialise once per job, not at import and not once per video.
    reader = make_reader(config, args.model_dir, not args.offline, args.engine, args.paddle_size)
    destination.mkdir(parents=True)
    metadata = {"version": __version__, "created_utc": datetime.now(timezone.utc).isoformat(),
                "config": asdict(config), "requested_layout": args.layout,
                "requested_languages": list(args.lang),
                "source": str(source), "video_count": len(videos), "dependencies": {},
                "engine": args.engine, "paddle_size": args.paddle_size if args.engine == "paddle" else None,
                "paddle_mkldnn": False if args.engine == "paddle" else None,
                "model_names": getattr(reader, "model_names", [])}
    for name in ("easyocr", "torch", "opencv-python-headless", "opencv-contrib-python", "numpy", "paddleocr", "paddlepaddle", "paddlex"):
        try:
            metadata["dependencies"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            metadata["dependencies"][name] = "not recorded"
    (destination / "run.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    results = []
    interrupted = False
    try:
        with (destination / "details.jsonl").open("w", encoding="utf-8") as stream:
            for number, video in enumerate(videos, 1):
                try:
                    local = config
                    platform = platform_from_path(video) if args.layout == "auto" else None
                    if args.layout == "auto" and platform is None:
                        row = {"path": str(video), "status": "skipped_layout", "needs_review": True,
                               "review_reasons": ["unknown_platform_use_explicit_layout"]}
                    elif (args.layout in {"auto", "reels"} and platform != "tiktok"
                          and "video" in video.stem.casefold() and "reel" not in video.stem.casefold()):
                        row = {"path": str(video), "status": "skipped_layout", "needs_review": True,
                               "review_reasons": ["feed_post_use_fixed_roi"]}
                    else:
                        if args.layout == "auto" and platform == "tiktok":
                            local = replace(config, layout="tiktok")
                        row = process_video(video, reader, local,
                                            destination / "screenshots" if args.screenshots or args.excel else None)
                except Exception as exc:
                    row = {"path": str(video), "status": "error", "needs_review": True,
                           "review_reasons": ["processing_error"], "error": f"{type(exc).__name__}: {exc}"}
                for shot in row.get("screenshots", []):
                    for key in ("path", "full_path"):
                        if key in shot:
                            shot[key] = Path(shot[key]).resolve().relative_to(destination.resolve()).as_posix()
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
                stream.flush()
                # Frame observations are already durable in JSONL; keep only summaries in RAM.
                for direction in ("forward", "reverse"):
                    if direction in row:
                        row[direction].pop("observations", None)
                results.append(row)
                print(f"[{number}/{len(videos)}] {video.name}: {row['status']}", flush=True)
    except KeyboardInterrupt:
        interrupted = True
        print("Interrupted; exporting completed videos.", file=sys.stderr)
    finally:
        save_csv(results, destination / "results.csv")
        save_review(results, destination / "review.html")
        if args.excel:
            from .excel import save_excel
            save_excel(results, destination / "results.xlsx")
    print(f"Saved {len(results)} video results in {destination}")
    return 130 if interrupted else (1 if any(r["status"] == "error" for r in results) else 0)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "review":
            from .review import serve
            return serve(args.folder, args.port, not args.no_open)
        if args.command == "manifest":
            folders = make_manifest(args.input)
            if not folders:
                raise ValueError("No video folders found")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(folders, stream, indent=2, ensure_ascii=False)
            print(f"Saved {len(folders)} folders; Slurm array range is 1-{len(folders)}")
            return 0
        if args.command == "duration":
            total, failed = 0.0, 0
            videos = discover_videos(args.input, recursive=True)
            if not videos:
                raise ValueError("No supported videos found")
            for video in videos:
                try:
                    with open_video(video) as (_, fps, count):
                        total += count / fps
                except Exception as exc:
                    failed += 1
                    print(f"{video}: {exc}", file=sys.stderr)
            print(f"{len(videos)-failed} videos; approximately {total:.2f} seconds ({total/3600:.2f} hours); {failed} failures")
            return 1 if failed else 0
        return run(args)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
