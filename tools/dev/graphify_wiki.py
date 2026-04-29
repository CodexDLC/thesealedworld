from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


def _existing_paths(paths: Iterable[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved in seen or not resolved.exists():
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def _candidate_site_packages(project_root: Path) -> list[Path]:
    candidates: list[Path] = []

    explicit = os.environ.get("GRAPHIFY_SITE_PACKAGES")
    if explicit:
        candidates.append(Path(explicit))

    candidates.extend(project_root.glob(".venv/Lib/site-packages"))

    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "uv" / "tools" / "graphifyy" / "Lib" / "site-packages")

    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        archive_root = Path(localappdata) / "uv" / "cache" / "archive-v0"
        if archive_root.exists():
            candidates.extend(sorted(archive_root.glob("*/Lib/site-packages"), reverse=True))

    return _existing_paths(candidates)


def _ensure_graphify_importable(project_root: Path) -> None:
    try:
        import graphify  # noqa: F401

        return
    except ImportError:
        pass

    for site_packages in _candidate_site_packages(project_root):
        if str(site_packages) not in sys.path:
            sys.path.insert(0, str(site_packages))
        try:
            import graphify  # noqa: F401

            return
        except ImportError:
            continue

    searched = "\n".join(f"- {path}" for path in _candidate_site_packages(project_root))
    raise SystemExit(
        "graphify package is not importable.\n"
        "Searched these site-packages locations:\n"
        f"{searched or '- <none>'}\n"
        "Run `uv sync --extra dev` or set GRAPHIFY_SITE_PACKAGES if graphifyy is installed elsewhere."
    )


def _load_graph(graph_path: Path):
    from networkx.readwrite import json_graph

    raw = json.loads(graph_path.read_text(encoding="utf-8"))
    try:
        return json_graph.node_link_graph(raw, edges="links")
    except TypeError:
        return json_graph.node_link_graph(raw)


def _collect_communities(graph) -> dict[int, list[str]]:
    communities: dict[int, list[str]] = defaultdict(list)
    for node_id, data in graph.nodes(data=True):
        community = data.get("community")
        if community is None:
            continue
        communities[int(community)].append(node_id)
    return dict(sorted(communities.items()))


def _load_cohesion(analysis_path: Path) -> dict[int, float]:
    if not analysis_path.exists():
        return {}
    raw = json.loads(analysis_path.read_text(encoding="utf-8"))
    cohesion = raw.get("cohesion", {})
    return {int(key): value for key, value in cohesion.items()}


def build_wiki(project_root: Path, graph_path: Path, output_dir: Path) -> int:
    from graphify.analyze import god_nodes
    from graphify.wiki import to_wiki

    graph = _load_graph(graph_path)
    communities = _collect_communities(graph)
    if not communities:
        raise SystemExit(
            f"No community metadata found in {graph_path}. Run graphify update/cluster before generating the wiki."
        )

    analysis_path = project_root / "graphify-out" / ".graphify_analysis.json"
    cohesion = _load_cohesion(analysis_path)
    labels = {community_id: f"Community {community_id}" for community_id in communities}
    articles = to_wiki(
        graph,
        communities,
        output_dir,
        community_labels=labels,
        cohesion=cohesion,
        god_nodes_data=god_nodes(graph),
    )
    return articles


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate graphify wiki pages from an existing graph.json without relying on a graphify wiki CLI command."
    )
    parser.add_argument(
        "project_root",
        nargs="?",
        default=".",
        help="Project root that contains graphify-out/ (default: current directory).",
    )
    parser.add_argument(
        "--graph",
        default=None,
        help="Path to graph.json. Defaults to <project_root>/graphify-out/graph.json.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output directory. Defaults to <project_root>/graphify-out/wiki.",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    graph_path = Path(args.graph).resolve() if args.graph else project_root / "graphify-out" / "graph.json"
    output_dir = Path(args.out).resolve() if args.out else project_root / "graphify-out" / "wiki"

    if not graph_path.exists():
        raise SystemExit(f"graph.json not found: {graph_path}")

    _ensure_graphify_importable(project_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    articles = build_wiki(project_root, graph_path, output_dir)
    print(f"graphify wiki generated: {articles} articles + index -> {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
