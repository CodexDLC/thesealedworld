# 08. LLM Node Pool Generation

Status: planned.

## Goal

Generate node pools and boundary descriptors from setting DNA instead of relying only on manual JSON.

## Scope

- Generate node pool entries without coordinates.
- Generate void surface/boundary descriptors per setting.
- Generate transition text fields for movement labels.
- Validate duplicate signatures through stable hashes.
- Allow manual entries and generated entries to coexist.

## Contract Questions Before Coding

- What exact setting DNA is passed to generation?
- How many pool nodes are generated in the first batch?
- How are duplicates detected and rejected?
- How do we expand the pool when a larger zone needs more active nodes?

## Exit Criteria

- Backend can request more node pool entries.
- Generated entries pass schema validation.
- Zone assembly can use generated and manual pool nodes interchangeably.
