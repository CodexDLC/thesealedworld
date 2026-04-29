# Development Tools

Small project-local helpers for validation, project maps, and graphify navigation.

## Quality Check

```powershell
python tools/dev/check.py
```

Runs the project quality gate through `codex_core.dev.check_runner`.

## Project Tree

```powershell
python tools/dev/generate_tree.py
```

Starts the interactive project tree generator.

## Graphify Wiki

```powershell
powershell -ExecutionPolicy Bypass -File tools/dev/graphify_wiki.ps1
```

Generates `graphify-out/wiki/` from an existing `graphify-out/graph.json`. This is useful because the installed `graphify` CLI can build/update the code graph, while this script directly calls `graphify.wiki.to_wiki` to produce Markdown navigation pages.

Typical flow:

```powershell
graphify update .
powershell -ExecutionPolicy Bypass -File tools/dev/graphify_wiki.ps1
```
