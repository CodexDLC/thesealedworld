from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = ROOT_DIR / ".env.grafana-cleanup"
DEFAULT_QUERY = '{container="tbmmorpg-tg-bot"} |= "BotSettings("'


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def auth_header(user: str, token: str) -> str:
    raw = f"{user}:{token}".encode()
    return "Basic " + base64.b64encode(raw).decode("ascii")


def loki_request(
    *,
    method: str,
    path: str,
    params: dict[str, str] | None,
    auth: str,
    timeout: float,
) -> tuple[int, str]:
    base_url = require_env("GRAFANA_LOKI_URL").rstrip("/")
    query = f"?{urlencode(params)}" if params else ""
    request = Request(
        url=f"{base_url}{path}{query}",
        method=method,
        headers={"Authorization": auth, "Accept": "application/json"},
    )

    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator-provided Grafana URL.
            body = response.read().decode("utf-8", errors="replace")
            return response.status, body
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except URLError as exc:
        raise SystemExit(f"Request failed: {exc}") from exc


def preview_logs(args: argparse.Namespace, auth: str) -> None:
    params = {
        "query": args.query,
        "start": args.start,
        "end": args.end,
        "limit": str(args.limit),
        "direction": "forward",
    }
    status, body = loki_request(
        method="GET",
        path="/loki/api/v1/query_range",
        params=params,
        auth=auth,
        timeout=args.timeout,
    )
    if status >= 400:
        raise SystemExit(f"Preview failed with HTTP {status}: {body}")

    payload = json.loads(body)
    streams: list[dict[str, Any]] = payload.get("data", {}).get("result", [])
    lines = [(stream.get("stream", {}), value) for stream in streams for value in stream.get("values", [])]
    print(f"Preview matched {len(lines)} returned log lines (limit={args.limit}).")
    for labels, value in lines[: args.limit]:
        timestamp, _line = value
        print(f"- {timestamp} {labels}")


def submit_delete(args: argparse.Namespace, auth: str) -> None:
    if not args.confirm_delete:
        print("Delete request was NOT submitted. Add --confirm-delete to create it.")
        return

    params = {
        "query": args.query,
        "start": args.start,
        "end": args.end,
    }
    status, body = loki_request(
        method="POST",
        path="/loki/api/v1/delete",
        params=params,
        auth=auth,
        timeout=args.timeout,
    )
    if status >= 400:
        raise SystemExit(f"Delete request failed with HTTP {status}: {body}")
    print(f"Delete request submitted. HTTP {status}: {body or '<empty response>'}")


def list_delete_requests(args: argparse.Namespace, auth: str) -> None:
    params = {"start": args.start, "end": args.end} if args.start and args.end else None
    status, body = loki_request(
        method="GET",
        path="/loki/api/v1/delete",
        params=params,
        auth=auth,
        timeout=args.timeout,
    )
    if status >= 400:
        raise SystemExit(f"List delete requests failed with HTTP {status}: {body}")
    print(body)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview and submit Grafana Cloud Loki log deletion requests.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--start", help="RFC3339 or unix timestamp, for example 2026-05-23T09:37:00Z.")
    parser.add_argument("--end", help="RFC3339 or unix timestamp, for example 2026-05-23T09:38:00Z.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--list-requests", action="store_true")
    parser.add_argument("--confirm-delete", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_file(args.env_file)

    user = require_env("GRAFANA_LOKI_USER")
    token = require_env("GRAFANA_LOKI_DELETE_TOKEN")
    auth = auth_header(user, token)

    if args.list_requests:
        list_delete_requests(args, auth)
        return 0

    if not args.start or not args.end:
        raise SystemExit("--start and --end are required unless --list-requests is used.")

    print(f"Query: {args.query}")
    print(f"Range: {args.start} -> {args.end}")
    preview_logs(args, auth)
    submit_delete(args, auth)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
