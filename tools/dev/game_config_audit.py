from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCAN_ROOTS = (
    PROJECT_ROOT / "src" / "backend",
    PROJECT_ROOT / "src" / "shared",
)

RUNTIME_HINTS = (
    "CHANCE",
    "MULT",
    "RATIO",
    "CAP",
    "LIMIT",
    "TTL",
    "SECONDS",
    "MINUTES",
    "TIMEOUT",
    "DELAY",
    "INTERVAL",
    "RATE",
    "WEIGHT",
    "THRESHOLD",
    "MAX",
    "MIN",
    "SEC",
    "WAIT",
    "DURATION",
)

CONTRACT_HINTS = (
    "TASK",
    "EVENT",
    "QUEUE",
    "PATH",
    "URL",
    "VERSION",
    "KEY",
    "REGISTRY",
    "BY_KEY",
)

CATALOG_PATH_HINTS = (
    "\\resources\\",
    "/resources/",
    "\\prompts\\",
    "/prompts/",
    "\\static\\",
    "/static/",
)


@dataclass(frozen=True)
class ConfigCandidate:
    path: str
    line: int
    name: str
    value_kind: str
    classification: str
    reason: str


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit uppercase constants for runtime config migration candidates.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of grouped text.")
    args = parser.parse_args()

    candidates = sorted(_scan(), key=lambda item: (item.classification, item.path, item.line, item.name))
    if args.json:
        print(json.dumps([asdict(item) for item in candidates], ensure_ascii=False, indent=2))
        return

    current = None
    for item in candidates:
        if item.classification != current:
            current = item.classification
            print(f"\n[{current}]")
        print(f"{item.path}:{item.line} {item.name} ({item.value_kind}) - {item.reason}")


def _scan() -> list[ConfigCandidate]:
    candidates: list[ConfigCandidate] = []
    for root in DEFAULT_SCAN_ROOTS:
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            candidates.extend(_scan_file(path))
    return candidates


def _scan_file(path: Path) -> list[ConfigCandidate]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    result: list[ConfigCandidate] = []
    rel = path.relative_to(PROJECT_ROOT).as_posix()
    for node in tree.body:
        name, value = _assignment(node)
        if not name or not name.isupper():
            continue
        value_kind = _value_kind(value)
        classification, reason = _classify(rel, name, value_kind)
        result.append(
            ConfigCandidate(
                path=rel,
                line=getattr(node, "lineno", 0),
                name=name,
                value_kind=value_kind,
                classification=classification,
                reason=reason,
            )
        )
    return result


def _assignment(node: ast.stmt) -> tuple[str | None, ast.AST | None]:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id, node.value
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id, node.value
    return None, None


def _value_kind(value: ast.AST | None) -> str:
    if isinstance(value, ast.Constant):
        return type(value.value).__name__
    if isinstance(value, ast.Dict):
        return "dict"
    if isinstance(value, ast.List):
        return "list"
    if isinstance(value, ast.Tuple):
        return "tuple"
    if isinstance(value, ast.Set):
        return "set"
    if isinstance(value, ast.Call):
        return "call"
    return type(value).__name__ if value is not None else "unknown"


def _classify(path: str, name: str, value_kind: str) -> tuple[str, str]:
    if "security" in path or name.startswith("PASSWORD_"):
        return "code_contract", "security-sensitive constant; keep outside Redis runtime tuning"
    tokens = _tokens(name)
    if tokens & set(CONTRACT_HINTS):
        return "code_contract", "transport, registry, version, key, or asset contract"
    if any(hint in path for hint in CATALOG_PATH_HINTS) or name.endswith(("_DB", "_CATALOG", "_REGISTRY")):
        return "catalog_later", "structured authored/catalog data; migrate through catalog storage, not scalar Redis"
    if value_kind in {"dict", "list", "tuple", "set"}:
        return "catalog_later", "structured value needs schema-specific admin and validation"
    if value_kind in {"int", "float", "bool", "UnaryOp", "BinOp"} and tokens & set(RUNTIME_HINTS):
        return "runtime_config", "scalar timing/balance/limit candidate for BaseGameConfig"
    return "ignore", "constant does not look like a runtime tuning knob"


def _tokens(name: str) -> set[str]:
    return {token for token in name.strip("_").split("_") if token}


if __name__ == "__main__":
    main()
