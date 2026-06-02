from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


class PreviewServer:
    def __init__(self, *, preview_root: Path, static_root: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
        self.preview_root = preview_root.resolve()
        self.static_root = static_root.resolve()
        self.host = host
        self.port = port

    def serve_forever(self) -> None:
        preview_root = self.preview_root
        static_root = self.static_root

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                request_path = unquote(parsed.path)
                if request_path == "/game/catalog/bootstrap":
                    self._send_json(_catalog_bootstrap_payload())
                    return
                if request_path == "/favicon.ico":
                    self.send_response(204)
                    self.end_headers()
                    return
                if request_path.startswith("/static/"):
                    file_path = static_root / request_path.removeprefix("/static/")
                    self._send_file(file_path, static_root)
                    return
                if request_path in ("", "/"):
                    file_path = preview_root / "index.html"
                else:
                    file_path = preview_root / request_path.lstrip("/")
                self._send_file(file_path, preview_root)

            def log_message(self, format: str, *args: object) -> None:
                return

            def _send_file(self, file_path: Path, allowed_root: Path) -> None:
                resolved = file_path.resolve()
                if not _is_within(resolved, allowed_root) or not resolved.is_file():
                    self.send_error(404)
                    return
                content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
                payload = resolved.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def _send_json(self, payload: dict[str, object]) -> None:
                encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        server = ThreadingHTTPServer((self.host, self.port), Handler)
        print(f"Serving game preview at http://{self.host}:{self.port}/")
        print("Press Ctrl+C to stop.")
        server.serve_forever()


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _catalog_bootstrap_payload() -> dict[str, object]:
    return {
        "version": "preview",
        "manifest": {"version": "preview", "catalogs": {}},
        "catalogs": {},
    }
