from __future__ import annotations

import json
import mimetypes
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .models import Flow, validate_flow
from .runner import FlowRunner
from .simulated import SimulatedDriver


STATIC = Path(__file__).resolve().parent / "static"


def create_handler(flow_path: Path):
    class StudioHandler(BaseHTTPRequestHandler):
        server_version = "TestStudio/0.3"

        def _json(self, status: int, payload: object) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/api/flow":
                self._json(HTTPStatus.OK, json.loads(flow_path.read_text(encoding="utf-8")))
                return
            path = STATIC / ("index.html" if self.path in {"/", ""} else self.path.removeprefix("/static/"))
            if not path.is_file() or STATIC not in path.resolve().parents:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_PUT(self) -> None:  # noqa: N802
            if self.path != "/api/flow":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                payload = self._read_json()
                flow = Flow.from_dict(payload)
                errors = validate_flow(flow)
                if errors:
                    self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"errors": errors})
                    return
                flow_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                self._json(HTTPStatus.OK, {"saved": True, "path": str(flow_path), "steps": len(flow.steps)})
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self._json(HTTPStatus.BAD_REQUEST, {"errors": [str(error)]})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/api/run":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                payload = self._read_json()
                flow = Flow.from_dict(payload)
                errors = validate_flow(flow)
                if errors:
                    self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"errors": errors})
                    return
                with tempfile.TemporaryDirectory(prefix="test-studio-") as directory:
                    result = FlowRunner(SimulatedDriver(), Path(directory)).run(flow)
                self._json(HTTPStatus.OK, result.to_dict())
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
                self._json(HTTPStatus.BAD_REQUEST, {"errors": [str(error)]})

        def log_message(self, format: str, *args) -> None:
            return

    return StudioHandler


def serve(flow_path: Path, host: str = "127.0.0.1", port: int = 4174) -> None:
    flow_path = flow_path.resolve()
    if not flow_path.is_file():
        raise FileNotFoundError(flow_path)
    server = ThreadingHTTPServer((host, port), create_handler(flow_path))
    print(f"Test Studio: http://{host}:{port}")
    print(f"Flow file: {flow_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
