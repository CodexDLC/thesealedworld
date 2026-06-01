# Development Tools

Small project-local helpers for validation, project maps, and graphify navigation.

## Quality Check

```powershell
python tools/dev/check.py
```

Runs the project quality gate: hooks, types, security audit, fixture validators, documentation build, and tests.

## Fixture Validators

```powershell
python tools/validators/run.py
```

Validates project fixtures such as scenario JSON graphs before tests run.

## Game Config Audit

```powershell
python tools/dev/game_config_audit.py
python tools/dev/game_config_audit.py --json
```

Classifies uppercase constants as `runtime_config`, `catalog_later`, `code_contract`, or `ignore`.
Use it before migrating new knobs into Redis-backed `BaseGameConfig` namespaces.

## Project Tree

```powershell
python tools/dev/generate_tree.py
```

Starts the interactive project tree generator.

## Reset Game Database

```powershell
python tools/dev/reset_game_db.py
```

Prints a dry-run plan for clearing game data in the current dev database while preserving site auth tables
(`auth_users`, `auth_refresh_tokens`, `alembic_version`).

To actually clear game data:

```powershell
python tools/dev/reset_game_db.py --yes
```

To keep loaded scenario content and only clear character/world/runtime game data:

```powershell
python tools/dev/reset_game_db.py --keep-scenario-content --yes
```

To keep loaded scenario and world content while clearing characters, monsters, item instances,
inventory, and other runtime game data:

```powershell
python tools/dev/reset_game_db.py --keep-scenario-content --keep-world-content --yes
```

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
