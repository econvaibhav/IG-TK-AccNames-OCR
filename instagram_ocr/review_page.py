"""Small review UI: escaped HTML, local assets, no hosted dependencies."""

import html
from pathlib import Path
import shutil
from urllib.parse import quote

from .review import evidence_path, row_id

LABELS = {"1sec": "1 second", "3sec": "3 seconds", "end_minus_1sec": "End − 1 second",
          "25percent": "25% · lower quartile", "50percent": "50% · median", "75percent": "75% · upper quartile"}


def save_review(results, path):
    path = Path(path)
    e = lambda x: html.escape(str(x), quote=True)
    cards = []
    for index, row in enumerate(results, 1):
        key = row_id(row)
        figures = []
        for shot in row.get("screenshots", []):
            label = LABELS.get(shot["label"], shot["label"])
            if "path" not in shot:
                figures.append(f'<figure class="missing"><figcaption>{e(label)}</figcaption><p>{e(shot.get("error", "unavailable").replace("_", " "))}</p></figure>')
                continue
            def url(field):
                return e(quote(evidence_path(shot[field], path.parent).relative_to(path.parent.resolve()).as_posix()))
            crop = url("path")
            full = url("full_path") if "full_path" in shot else crop
            time = f'{shot.get("seconds", 0):.2f} s · frame {shot.get("frame", "?")}'
            figures.append(f'<figure><figcaption><strong>{e(label)}</strong><span>{e(time)}</span></figcaption>'
                           f'<button class="frame-open" type="button" data-full="{full}" data-caption="{e(label + " · " + time)}" aria-label="Enlarge {e(label)} frame">'
                           f'<img class="full-frame" src="{full}" loading="lazy" alt="Full frame at {e(label)}"></button>'
                           f'<img class="crop" src="{crop}" loading="lazy" alt="Account crop at {e(label)}">'
                           f'<small>{"Account crop · click frame to enlarge" if shot.get("roi_found") else "Crop not found · inspect full frame"}</small></figure>')
        readings = []
        for direction in ("forward", "reverse"):
            names = row.get(direction, {}).get("candidates", [])
            value = "; ".join(f"{c['name']} ({c['votes']} votes)" for c in names) or "No reading"
            readings.append(f'<div><span class="eyebrow">{direction.title()} pass</span><p>{e(value)}</p></div>')
        names = "\n".join(row.get("union_names", []))
        reasons = ", ".join(r.replace("_", " ") for r in row.get("review_reasons", [])) or "No automatic flag"
        pictures = ''.join(figures) or '<p>No frames were saved for this video.</p>'
        cards.append(f'''<article data-id="{key}">
<div class="card-heading"><div><span class="eyebrow">CLIP {index:03d}</span><h2>{e(Path(row['path']).name)}</h2></div><span class="badge">Unreviewed</span></div>
<p class="source">{e(row['path'])}</p>
<div class="readings">{''.join(readings)}<div><span class="eyebrow">Comparison</span><p>{e(row['status'])}</p></div></div>
<p class="reason">{e(reasons)} {e(row.get('error', ''))}</p>
<div class="pictures">{pictures}</div>
<form><div class="edit-grid"><label>Account name(s)<textarea name="names" rows="2" maxlength="1000" data-original="{e(names)}" autocomplete="off" spellcheck="false" placeholder="Account name">{e(names)}</textarea></label>
<div class="review-checks"><label><input name="reviewed" type="checkbox" checked> Mark as reviewed</label><label><input name="unreadable" type="checkbox"> Cannot read</label></div></div>
<p class="hint">Keep the name if it is correct, or edit it. Use one line per account. Display names and all languages are welcome.</p>
<label>Note <span class="optional">(optional)</span><input name="notes" maxlength="2000" placeholder="e.g. Dot before pl, not a hyphen"></label>
<div class="save-row"><button type="submit" disabled>Save changes</button><span class="save-status" role="status">Start the local review server to edit.</span></div></form></article>''')
    path.write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Account OCR review</title><link rel="stylesheet" href="review.css"><script src="review.js" defer></script></head><body>
<header><div><span class="eyebrow">INSTAGRAM / TIKTOK · ACCOUNT OCR</span><h1>Review the evidence.<br>Keep the right name.</h1><p>Inspect six moments, check the account name, and save to Excel.</p></div><div class="progress"><strong id="count">—</strong><span>clips resolved</span></div></header>
<nav><label class="search">Find a clip or account<input id="search" type="search" placeholder="Search filenames and names"></label><label class="filter"><input id="pending" type="checkbox"> Unresolved only</label><div class="downloads"><a href="reviewed.xlsx" download>Download Excel</a><button id="export" type="button" disabled>Refresh Excel</button></div></nav>
<p id="connection" role="status">Connecting to the local review server…</p>
<main>''' + ''.join(cards) + '''</main><p id="empty" hidden>No clips match this filter.</p>
<footer>Save updates reviewed.xlsx. Your original OCR readings remain available. Editing Excel does not change this review.</footer>
<dialog id="lightbox"><button id="close" type="button">Close</button><p id="caption"></p><img id="enlarged" alt="Full video frame"></dialog></body></html>''', encoding="utf-8")
    for suffix in ("css", "js"):
        shutil.copyfile(Path(__file__).parent / "static" / f"review.{suffix}", path.parent / f"review.{suffix}")
