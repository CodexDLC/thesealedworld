from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Probe:
    name: str
    path: str
    expected_status: int = 200
    expected_text: str | None = None
    expected_json_key: str | None = None


PROBES = (
    Probe("nginx health", "/health/nginx", expected_text="ok"),
    Probe("frontend health", "/health/frontend", expected_json_key="status"),
    Probe("backend health", "/health/backend", expected_json_key="status"),
    Probe("chat health", "/health/chat", expected_json_key="status"),
    Probe("frontend static", "/static/css/site.css"),
    Probe("backend openapi", "/openapi.json", expected_json_key="openapi"),
)


def request(base_url: str, probe: Probe, timeout: float) -> bytes:
    url = f"{base_url.rstrip('/')}{probe.path}"
    req = Request(url, headers={"User-Agent": "tbmmorpg-nginx-smoke/1.0"})
    with urlopen(req, timeout=timeout) as response:  # noqa: S310 - local/provided smoke target
        status = response.status
        body = response.read()
    if status != probe.expected_status:
        raise RuntimeError(f"{probe.name}: expected {probe.expected_status}, got {status}")
    return body


def validate_body(probe: Probe, body: bytes) -> None:
    text = body.decode("utf-8", errors="replace")
    if probe.expected_text is not None and probe.expected_text not in text:
        raise RuntimeError(f"{probe.name}: expected text {probe.expected_text!r}")
    if probe.expected_json_key is not None:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{probe.name}: expected JSON body") from exc
        if probe.expected_json_key not in payload:
            raise RuntimeError(f"{probe.name}: missing JSON key {probe.expected_json_key!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the local nginx reverse proxy layer.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    failed = False
    for probe in PROBES:
        try:
            body = request(args.base_url, probe, args.timeout)
            validate_body(probe, body)
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            failed = True
            print(f"FAIL {probe.name}: {exc}", file=sys.stderr)
        else:
            print(f"PASS {probe.name}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
