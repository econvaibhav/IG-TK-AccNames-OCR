"""Check installed entry points and assets; CI runs this outside the checkout."""

from importlib import metadata, resources
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen

import ig_tk_ocr
from ig_tk_ocr.review import ReviewStore, make_server, row_id
from ig_tk_ocr.review_page import save_review


class DistributionTests(unittest.TestCase):
    def test_metadata_and_packaged_assets(self):
        self.assertEqual(metadata.version("ig-tk-accnames-ocr"), ig_tk_ocr.__version__)
        for filename in ("review.js", "review.css"):
            asset = resources.files("ig_tk_ocr").joinpath("static", filename)
            self.assertTrue(asset.is_file(), filename)
            self.assertGreater(len(asset.read_bytes()), 100)

    def test_console_script_outside_checkout(self):
        script = Path(sysconfig.get_path("scripts")) / "ig-tk-accnames-ocr"
        self.assertTrue(script.is_file(), f"Missing console script: {script}")
        with tempfile.TemporaryDirectory() as outside:
            for argument, expected in (("--help", "review"),
                                       ("--version", ig_tk_ocr.__version__),
                                       ("--list-languages", "Bulgarian")):
                result = subprocess.run(
                    [sys.executable, "-I", str(script), argument], cwd=outside,
                    check=True, capture_output=True, text=True, timeout=20,
                )
                self.assertIn(expected, result.stdout)

    def test_review_serves_assets_and_saves_excel(self):
        from openpyxl import load_workbook

        with tempfile.TemporaryDirectory() as outside:
            folder = Path(outside)
            row = {"path": "example.mp4", "status": "agreement",
                   "union_names": ["Новини България"], "needs_review": False}
            (folder / "details.jsonl").write_text(
                json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            save_review([row], folder / "review.html")
            store = ReviewStore(folder)
            server = make_server(store)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                with urlopen(base + "/", timeout=10) as response:
                    self.assertIn("Новини България", response.read().decode("utf-8"))
                for filename in ("review.js", "review.css"):
                    with urlopen(base + "/" + filename, timeout=10) as response:
                        expected = resources.files("ig_tk_ocr").joinpath("static", filename)
                        self.assertEqual(response.read(), expected.read_bytes())
                with urlopen(base + "/api/state", timeout=10) as response:
                    state = json.load(response)
                body = {"id": row_id(row), "revision": state["revision"],
                        "names": row["union_names"], "reviewed": True,
                        "unreadable": False, "notes": ""}
                request = Request(base + "/api/save", json.dumps(body).encode("utf-8"),
                                  {"Content-Type": "application/json",
                                   "X-Review-Token": state["token"]})
                with urlopen(request, timeout=10) as response:
                    self.assertEqual(json.load(response)["export_errors"], [])
                with urlopen(base + "/reviewed.xlsx", timeout=10) as response:
                    workbook = load_workbook(BytesIO(response.read()))
                try:
                    cells = list(workbook.active.values)
                    result = dict(zip(cells[0], cells[1]))
                    self.assertEqual(result["review_status"], "confirmed")
                    self.assertEqual(json.loads(result["final_names"]), row["union_names"])
                finally:
                    workbook.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
