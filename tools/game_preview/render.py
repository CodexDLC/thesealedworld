from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from jinja2 import Environment, FileSystemLoader, select_autoescape

from tools.game_preview.fixtures import PreviewFixture, build_fixture
from tools.game_preview.server import PreviewServer

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT / "src" / "frontend" / "templates"
STATIC_DIR = ROOT / "src" / "frontend" / "static"
DEFAULT_OUT_DIR = ROOT / "tmp" / "game_preview"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    params = _parse_params(args.param)
    fixture = build_fixture(args.fixture, params)
    template_name = args.template or fixture.template
    out_path = _output_path(args.out, args.fixture, template_name)
    html = render_preview(template_name=template_name, fixture=fixture, wrap=not args.fragment)
    write_preview(html, out_path)
    print(f"Rendered {args.fixture} -> {out_path}")
    if args.serve:
        index_path = out_path.parent / "index.html"
        if out_path.name != "index.html":
            index_path.write_text(html, encoding="utf-8")
        PreviewServer(preview_root=out_path.parent, static_root=STATIC_DIR, host=args.host, port=args.port).serve_forever()
    return 0


def render_preview(*, template_name: str, fixture: PreviewFixture, wrap: bool = True) -> str:
    env = create_environment()
    body = env.get_template(template_name).render(**fixture.context)
    if not wrap:
        return body
    return _wrap_html(body=body, fixture=fixture, template_name=template_name)


def write_preview(html: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")


def create_environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(("html", "xml")),
    )
    env.globals["inline_css"] = _inline_css
    env.filters["scenario_rich_text"] = _scenario_rich_text
    env.filters["split_bracket_coords"] = _split_bracket_coords
    env.filters["combat_log_time"] = _combat_log_time
    return env


def _wrap_html(*, body: str, fixture: PreviewFixture, template_name: str) -> str:
    context = fixture.context
    domain = str(context.get("domain") or "")
    char_id = context.get("char_id") or ""
    status_seed = context.get("status_seed") or {"character_id": char_id, "hp": 0, "max_hp": 1}
    static_version = _static_version()
    active_char_id = json.dumps(str(char_id), ensure_ascii=False)
    domain_json = json.dumps(domain, ensure_ascii=False)
    status_json = json.dumps(status_seed, ensure_ascii=False)
    body_class = f"game-body {fixture.body_class}".strip()
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{_escape_text(fixture.title)}</title>
    <link rel="stylesheet" href="/static/css/fonts.css?v={static_version}">
    <link rel="stylesheet" href="/static/css/game.css?v={static_version}">
    <style>
        [x-cloak] {{ display: none !important; }}
        .game-preview-meta {{
            position: fixed;
            right: 8px;
            bottom: 8px;
            z-index: 2000;
            max-width: min(460px, calc(100vw - 16px));
            padding: 6px 8px;
            border: 1px solid rgba(255, 170, 0, .22);
            background: rgba(0, 0, 0, .72);
            color: rgba(255, 232, 190, .72);
            font: 10px/1.35 monospace;
            pointer-events: none;
        }}
    </style>
    <script src="/static/js/vendor/htmx.js" defer></script>
    <script src="/static/js/vendor/popper.js" defer></script>
    <script src="/static/js/vendor/tippy.js" defer></script>
    <script src="/static/js/game.js?v={static_version}" defer></script>
    <script src="/static/js/vendor/alpine-persist.js" defer></script>
    <script src="/static/js/vendor/alpine-collapse.js" defer></script>
    <script src="/static/js/vendor/alpine.js" defer></script>
    <script src="/static/js/core/status.js" defer></script>
</head>
<body class="{body_class}">
    <div id="app-viewport"
         class="game-container"
         data-domain="{_escape_attr(domain)}"
         x-data='gameShell({{ activeCharId: {active_char_id}, domain: {domain_json}, initialStatus: {status_json} }})'
         :style="`--chat-height: ${{chatHeight + 'px'}}`"
         @panel-toggle.window="togglePanel($event.detail)"
         @game-modal-open.window="openUnavailableModal($event.detail)"
         @hud-window-toggle.window="toggleHudWindow($event.detail?.name)"
         @chat-unread.window="if (chatClosed) chatUnread = true">
        <main id="main-content">
            <div class="shell-constrained">
{body}
            </div>
        </main>
    </div>
    <div class="game-preview-meta">
        fixture: {_escape_text(fixture.title)}<br>
        template: {_escape_text(template_name)}<br>
        css: /static/css/game.css
    </div>
</body>
</html>
"""


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render game Jinja templates with preview fixtures.")
    parser.add_argument("--fixture", required=True, help="Fixture key, for example combat/active_8_abilities.")
    parser.add_argument("--template", help="Template path under src/frontend/templates. Defaults to fixture template.")
    parser.add_argument("--out", help="Output HTML path. Defaults to tmp/game_preview/<fixture>.html.")
    parser.add_argument("--param", action="append", default=[], help="Fixture parameter as key=value. May be repeated.")
    parser.add_argument("--fragment", action="store_true", help="Write only rendered template HTML, without preview wrapper.")
    parser.add_argument("--serve", action="store_true", help="Serve output directory and /static assets after rendering.")
    parser.add_argument("--host", default="127.0.0.1", help="Preview server host.")
    parser.add_argument("--port", type=int, default=8765, help="Preview server port.")
    return parser.parse_args(argv)


def _parse_params(values: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for value in values:
        key, sep, raw = value.partition("=")
        if not sep or not key:
            raise ValueError(f"Invalid --param {value!r}; expected key=value.")
        params[key] = raw
    return params


def _output_path(raw_out: str | None, fixture_key: str, template_name: str) -> Path:
    if raw_out:
        path = Path(raw_out)
        return path if path.is_absolute() else ROOT / path
    safe_fixture = re.sub(r"[^a-zA-Z0-9_.-]+", "_", fixture_key).strip("_")
    safe_template = re.sub(r"[^a-zA-Z0-9_.-]+", "_", template_name).strip("_")
    return DEFAULT_OUT_DIR / f"{safe_fixture}__{safe_template}.html"


def _inline_css(file_path: str) -> str:
    try:
        return (STATIC_DIR / file_path).read_text(encoding="utf-8")
    except OSError:
        return ""


def _static_version() -> str:
    paths = (
        STATIC_DIR / "css" / "fonts.css",
        STATIC_DIR / "css" / "game.css",
        STATIC_DIR / "js" / "game.js",
    )
    mtimes = []
    for path in paths:
        try:
            mtimes.append(int(path.stat().st_mtime))
        except OSError:
            mtimes.append(0)
    return str(max(mtimes) if mtimes else 0)


def _scenario_rich_text(text: str) -> str:
    if not text:
        return text
    pattern = r"(?<![а-яa-z])([А-ЯA-Z0-9\s\.,!\?\-\:\%\#\[\]]{8,})(?![а-яa-z])"

    def repl(match: re.Match[str]) -> str:
        segment = match.group(1).strip()
        if any(char.isupper() for char in segment) and len(segment) > 5:
            return f'<span class="system-alert">{segment}</span>'
        return match.group(0)

    return re.sub(pattern, repl, text)


def _split_bracket_coords(value: str | None) -> dict[str, str | None]:
    if not value:
        return {"label": "", "coords": None}
    text = str(value).strip()
    match = re.match(r"^(?P<label>.*?)\s*\[(?P<coords>-?\d+\s*:\s*-?\d+)\]\s*$", text)
    if not match:
        return {"label": text, "coords": None}
    return {"label": match.group("label").strip(), "coords": match.group("coords").replace(" ", "")}


def _combat_log_time(timestamp: int | float | str | None) -> str:
    if timestamp in (None, ""):
        return ""
    try:
        return datetime.fromtimestamp(float(cast("Any", timestamp))).strftime("%H:%M:%S")
    except (TypeError, ValueError, OSError):
        return ""


def _escape_text(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attr(value: str) -> str:
    return _escape_text(value).replace('"', "&quot;")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
