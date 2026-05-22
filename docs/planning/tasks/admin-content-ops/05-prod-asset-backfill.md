# Task 05 - Production Asset Backfill

## Implementation Status

- [x] Operator backfill script added at `scripts/backfill_generated_assets_to_s3.py`.
- [x] Supports dry-run, skip-existing, relative storage keys, and report counters.
- [x] Covered with fake storage unit tests.
- [x] Real S3 credentials verified with a single smoke upload.
- [ ] Production dry-run/backfill pending server asset root access.

## Goal

Copy existing production generated assets from the current Docker volume/local
asset tree into S3 while preserving `storage_key` paths and old public URLs.

## Context

Production currently uses generated asset mounts/volumes:

- `deploy/compose.site.yml`
- `deploy/compose.game.yml`
- `deploy/docker-compose.yml`

The migration should copy files, not regenerate images.

## Scope

- Add an operator script that scans a local generated asset root.
- Upload each file to S3 using the same relative path as `storage_key`.
- Support dry-run mode.
- Support skip-existing mode.
- Produce a report:
  - uploaded count
  - skipped count
  - failed files
  - total bytes
- Do not rewrite database URLs by default.
- Keep rollback possible by leaving the production volume mounted for at least one release.

## Acceptance Checks

- Script can run in dry-run mode without credentials.
- Script uploads files preserving relative path.
- Re-running script is idempotent with skip-existing.
- Report is clear enough for manual production rollout.
- No AI regeneration is triggered.
- No DB migration is required when `/static/generated-assets/<storage_key>` stays stable.

## Handoff Prompt

```text
We are working in C:\install\projects\pets\TurnBasedMMORPG.

Read first:
- docs/agent-skills/turnbasedmmorpg-project/SKILL.md
- docs/agent-skills/turnbasedmmorpg-backend/SKILL.md
- docs/agent-skills/turnbasedmmorpg-deployment-management/SKILL.md
- docs/agent-skills/turnbasedmmorpg-testing-strategy/SKILL.md

Task:
Add a production asset backfill script that copies existing generated asset
files into S3 while preserving storage_key-relative paths. Do not regenerate
images and do not rewrite database URLs by default.

Relevant files:
- src/backend/features/generation_ai/asset_storage.py
- scripts/
- deploy/compose.site.yml
- deploy/compose.game.yml
- deploy/docker-compose.yml
- docs/ru/management/deployment.md
- docs/planning/tasks/admin-content-ops/05-prod-asset-backfill.md

Rules:
- The migration copies files only.
- Preserve storage_key paths.
- Include dry-run and skip-existing modes.
- Leave the current production volume as rollback/cache for one release.

Verification:
- Add tests around path scanning, key normalization, skip-existing behavior, and reporting.
- Run the narrowest relevant tests.
- Provide a production runbook command example in docs, but do not include real secrets.
```
