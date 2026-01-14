"""Local, durable human corrections and spreadsheet exports."""

from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, HTTPServer
import copy
import json
import mimetypes
import os
from pathlib import Path
import secrets
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit
import webbrowser

from .files import csv_row


def row_id(row):
    return sha256(row["path"].encode("utf-8")).hexdigest()[:20]


def evidence_path(value, root):
    """Resolve new relative evidence and legacy absolute paths after moving a run."""
    path = Path(value)
    if path.is_absolute():
        parts = path.parts
        if "screenshots" not in parts:
            raise ValueError("Evidence must be inside the screenshots folder")
        path = Path(*parts[parts.index("screenshots"):])
    resolved = (root / path).resolve()
    resolved.relative_to(root.resolve())
    return resolved


def atomic_write(path, writer):
    path = Path(path)
    descriptor, temp = tempfile.mkstemp(prefix=f".{path.stem}_", suffix=path.suffix, dir=path.parent)
    os.close(descriptor)
    try:
        writer(Path(temp))
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


class Conflict(ValueError):
    pass


class ReviewStore:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.results = []
        with (self.folder / "details.jsonl").open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    row = json.loads(line)
                    for direction in ("forward", "reverse"):
                        row.get(direction, {}).pop("observations", None)
                    for shot in row.get("screenshots", []):
                        for key in ("path", "full_path"):
                            if key in shot:
                                shot[key] = evidence_path(shot[key], self.folder).relative_to(self.folder).as_posix()
                    self.results.append(row)
        self.by_id = {row_id(row): row for row in self.results}
        if len(self.by_id) != len(self.results):
            raise ValueError("Duplicate video paths in details.jsonl")
        self.path = self.folder / "review_state.json"
        self.state = {"schema": 1, "revision": 0, "entries": {}, "history": []}
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
            if self.state.get("schema") != 1 or not isinstance(self.state.get("entries"), dict):
                raise ValueError("Unsupported or damaged review_state.json; keep it for recovery")
            if set(self.state["entries"]) - set(self.by_id):
                raise ValueError("Review corrections do not match this run's videos")

    def snapshot(self):
        return {"revision": self.state["revision"], "entries": self.state["entries"],
                "total": len(self.results), "reviewed": sum(
                    entry["decision"] in {"confirmed", "corrected"}
                    for entry in self.state["entries"].values())}

    def save(self, payload):
        if payload.get("revision") != self.state["revision"]:
            raise Conflict("This review changed in another tab. Reload before saving.")
        key = payload.get("id")
        if key not in self.by_id:
            raise ValueError("Unknown video")
        value, notes = payload.get("names", []), payload.get("notes", "")
        # New pages send a list: commas inside a display name stay intact.
        # Keep the old API readable for existing review pages and saved runs.
        if isinstance(value, str):
            value = value.replace(",", "\n").splitlines()
        if not isinstance(value, list) or len(value) > 32 or not all(isinstance(n, str) for n in value):
            raise ValueError("Enter one account name per line")
        if not isinstance(notes, str) or len(notes) > 2000 or sum(len(n) for n in value) > 1000:
            raise ValueError("Account names or notes are too long")
        names = list(dict.fromkeys(unicodedata.normalize("NFC", n.strip()) for n in value if n.strip()))
        for name in names:
            if len(name) > 200 or any(unicodedata.category(c) in {"Cc", "Cs"} for c in name):
                raise ValueError("An account name must be at most 200 characters and contain no control characters")
        original = self.by_id[key].get("union_names", [])
        key_for = lambda n: unicodedata.normalize("NFC", n.strip().lstrip("@")).casefold()
        unchanged = {key_for(n) for n in names} == {key_for(n) for n in original}
        if "reviewed" in payload or "unreadable" in payload:
            reviewed, unreadable = payload.get("reviewed", False), payload.get("unreadable", False)
            if type(reviewed) is not bool or type(unreadable) is not bool:
                raise ValueError("Review checkboxes must be true or false")
            if reviewed and unreadable:
                raise ValueError("Choose Mark as reviewed or Cannot read")
            decision = "unreadable" if unreadable else ("confirmed" if unchanged else "corrected") if reviewed else "unreviewed"
        else:
            decision = payload.get("decision")
            if decision not in {"unreviewed", "confirmed", "corrected", "unreadable"}:
                raise ValueError("Choose a review decision")
            if decision in {"confirmed", "corrected"}:
                decision = "confirmed" if unchanged else "corrected"
        if decision in {"confirmed", "corrected"} and not names:
            raise ValueError("Enter an account name, or tick Cannot read")
        updated = datetime.now(timezone.utc).isoformat(timespec="seconds")
        entry = {"decision": decision, "names": names, "notes": notes.strip(), "updated_utc": updated}
        new_state = copy.deepcopy(self.state)
        new_state["revision"] += 1
        new_state["history"].append({"revision": new_state["revision"], "id": key,
                                     "before": new_state["entries"].get(key), "after": entry})
        new_state["entries"][key] = entry
        atomic_write(self.path, lambda p: p.write_text(json.dumps(new_state, indent=2, ensure_ascii=False), encoding="utf-8"))
        self.state = new_state
        return self.export()

    def reviewed_rows(self):
        rows = []
        for result in self.results:
            entry = self.state["entries"].get(row_id(result), {})
            decision = entry.get("decision", "unreviewed")
            final = result.get("union_names", []) if decision == "unreviewed" else [] if decision == "unreadable" else entry.get("names", [])
            row = csv_row(result)
            row.update(review_status=decision, final_names=json.dumps(final, ensure_ascii=False),
                       review_notes=entry.get("notes", ""), reviewed_utc=entry.get("updated_utc", ""),
                       review_revision=self.state["revision"],
                       needs_manual_review=decision in {"unreviewed", "unreadable"})
            rows.append(row)
        return rows

    def export(self):
        """Refresh the one user-facing workbook from the durable review state."""
        try:
            from .excel import save_excel
            atomic_write(self.folder / "reviewed.xlsx", lambda path: save_excel(
                self.results, path, rows=self.reviewed_rows(), evidence_root=self.folder))
        except (OSError, ImportError) as exc:
            return [f"reviewed.xlsx: {type(exc).__name__}. Close the workbook if it is open and retry Refresh Excel."]
        return []


@contextmanager
def folder_lock(folder):
    """Only one review server may write this folder at a time; OS releases on exit."""
    with (folder / ".review.lock").open("a+b") as stream:
        try:
            if os.name == "nt":
                import msvcrt
                stream.seek(0); stream.write(b"0"); stream.flush(); stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("A review server already has this folder open. Use its browser tab.") from exc
        yield


def make_server(store, port=0):
    token = secrets.token_urlsafe(24)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, code, body, kind="application/json; charset=utf-8"):
            if isinstance(body, dict):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def allowed_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.allowed_host():
                return self.reply(403, {"error": "Use the printed local review URL"})
            request = unquote(urlsplit(self.path).path)
            if request == "/api/state":
                return self.reply(200, {**store.snapshot(), "token": token})
            if request == "/reviewed.xlsx":
                errors = store.export()
                relevant = [e for e in errors if e.startswith(request[1:])]
                if relevant:
                    return self.reply(503, {"error": " ".join(relevant)})
            relative = "review.html" if request == "/" else request.lstrip("/")
            if relative not in {"review.html", "review.js", "review.css", "reviewed.xlsx"} and not relative.startswith("screenshots/"):
                return self.reply(404, {"error": "Not found"})
            path = (store.folder / relative).resolve()
            if not path.is_relative_to(store.folder) or not path.is_file():
                return self.reply(404, {"error": "Not found"})
            return self.reply(200, path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if not self.allowed_host() or self.headers.get("Origin", origin) != origin or self.headers.get("X-Review-Token") != token:
                return self.reply(403, {"error": "Reload the local review page"})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.reply(415, {"error": "Expected JSON"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("Expected a JSON object")
                if self.path == "/api/save":
                    errors = store.save(payload)
                elif self.path == "/api/export":
                    errors = store.export()
                else:
                    return self.reply(404, {"error": "Not found"})
                return self.reply(200, {**store.snapshot(), "export_errors": errors})
            except Conflict as exc:
                return self.reply(409, {"error": str(exc)})
            except (ValueError, TypeError) as exc:
                return self.reply(400, {"error": str(exc)})
            except OSError as exc:
                return self.reply(500, {"error": f"Could not save: {exc}. Keep this page open and retry."})
    return HTTPServer(("127.0.0.1", port), Handler)


def serve(folder, port=0, open_browser=True):
    store = ReviewStore(folder)
    with folder_lock(store.folder):
        from .files import save_review
        save_review(store.results, store.folder / "review.html")
        for error in store.export():
            print(error, flush=True)
        with make_server(store, port) as server:
            url = f"http://127.0.0.1:{server.server_port}/"
            print(f"\nReview: {url}\nCorrections and exports: {store.folder}\nKeep this terminal open. Press Ctrl+C to stop; saved corrections remain.", flush=True)
            if open_browser:
                webbrowser.open(url)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("\nReview closed. Saved corrections are on disk.")
    return 0
