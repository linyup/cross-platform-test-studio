from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from test_studio.web import create_handler


ROOT = Path(__file__).resolve().parents[1]


class StudioWebTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.flow = Path(self.directory.name) / "flow.json"
        self.flow.write_text((ROOT / "examples/create-note.flow.json").read_text(encoding="utf-8"), encoding="utf-8")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(self.flow))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.directory.cleanup()

    def request(self, path: str, method: str = "GET", payload: dict | None = None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{self.base_url}{path}", data=data, method=method, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, response.read(), response.headers.get_content_type()

    def test_serves_authoring_ui_and_flow(self):
        status, body, content_type = self.request("/")
        self.assertEqual(200, status)
        self.assertEqual("text/html", content_type)
        self.assertIn(b"Test Studio", body)
        status, body, _ = self.request("/api/flow")
        self.assertEqual("create-note", json.loads(body)["id"])

    def test_saves_and_runs_flow(self):
        payload = json.loads(self.flow.read_text())
        payload["title"] = "Updated demo"
        status, body, _ = self.request("/api/flow", "PUT", payload)
        self.assertEqual(200, status)
        self.assertTrue(json.loads(body)["saved"])
        status, body, _ = self.request("/api/run", "POST", payload)
        result = json.loads(body)
        self.assertEqual("passed", result["status"])
        self.assertEqual(3, len(result["steps"]))


if __name__ == "__main__":
    unittest.main()
