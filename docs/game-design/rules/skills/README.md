# Skills Rules

This folder contains reviewed technical design references for the skill system.

- [Progression Reference](./progression_reference.md)
- [Catalog Reference](./catalog_reference.md)
- [Combat Runtime Reference](./combat_runtime_reference.md)
- Player-facing library source: [`library/rpg/skills/`](../../library/rpg/skills/README.md)

Current runtime catalog and DTO ownership lives in:

```text
src/backend/features/game_catalog/skills/
```

Do not copy old schema notes into this folder. Field-level DTO and catalog
contracts should be documented in `docs/ru` or derived from code when the stable
domain documentation is updated.
