"""Portable file discovery, manifests and review exports."""

import csv
import html
import json
from pathlib import Path
import re
from urllib.parse import quote

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
    path = Path(path)
    e = lambda x: html.escape(str(x), quote=True)
    cards = []
    for row in results:
        pictures = []
        for shot in row.get("screenshots", []):
            if "path" not in shot:
                continue
            relative = Path(shot["path"]).resolve().relative_to(path.parent.resolve()).as_posix()
            label = shot["label"].replace("_", " ")
            found = "account crop" if shot["roi_found"] else "full frame; crop not found"
            pictures.append(f'<figure><img src="{e(quote(relative))}" alt="OCR evidence"><figcaption>{e(label)}: {found}</figcaption></figure>')
        readings = []
        for direction in ("forward", "reverse"):
            candidates = row.get(direction, {}).get("candidates", [])
            value = "; ".join(f"{c['name']} ({c['votes']} frames)" for c in candidates) or "No reading"
            readings.append(f'<tr><th scope="row">{direction.title()}</th><td>{e(value)}</td></tr>')
        review = "Yes" if row.get("needs_review", True) else "No automatic flag"
        reasons = ", ".join(x.replace("_", " ") for x in row.get("review_reasons", []))
        cards.append(
            f'<article><h2>{e(Path(row["path"]).name)}</h2>'
            f'<p><b>Candidate:</b> {e(", ".join(row.get("union_names", [])) or "No account label found")}</p>'
            f'<table><tbody>{"".join(readings)}</tbody></table>'
            f'<p><b>Comparison:</b> {e(row["status"])} &nbsp; <b>Review:</b> {review}</p>'
            f'<p>{e(reasons)}</p><p>{e(row.get("error", ""))}</p>'
            f'<div class="pictures">{"".join(pictures)}</div></article>'
        )
    path.write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Account OCR review</title><style>'
        'body{font:16px/1.5 Arial,sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#111;background:#fff}'
        'article{border:1px solid #111;padding:24px;margin:24px 0}p{overflow-wrap:anywhere}'
        'table{border-collapse:collapse;width:100%;max-width:750px}th,td{border:1px solid #777;padding:8px 12px;text-align:left}'
        'th{width:100px}.pictures{display:flex;flex-wrap:wrap;gap:20px;margin-top:24px}'
        'figure{margin:0;max-width:100%}img{display:block;max-width:100%;max-height:240px;object-fit:contain;border:1px solid #777}'
        'figcaption{font-size:13px;margin-top:6px}h1{font-size:26px}h2{font-size:20px;margin-top:0}'
        '</style></head><body><h1>Account OCR review</h1>'
        '<p>Compare the detected names with the three saved crops.</p>' + ''.join(cards) + '</body></html>',
        encoding="utf-8",
    )
