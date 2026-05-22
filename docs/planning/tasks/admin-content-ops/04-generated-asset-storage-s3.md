# Task 04 - Generated Asset Storage S3

## Implementation Status

- [x] `S3GeneratedAssetStorage` added behind the generated asset storage abstraction.
- [x] S3 config validates required settings and keeps `storage_key` canonical.
- [x] Hetzner Nuremberg example values documented.
- [x] Covered with fake S3 client unit tests.
- [x] Frontend serves `/static/generated-assets/<storage_key>` from S3 when `ASSET_STORAGE_BACKEND=s3`.
- [x] `uv.lock` updated and real Hetzner Object Storage smoke upload verified.

## Goal

Implement S3-backed generated asset storage for production while keeping local
storage as the default for development and tests.

## Context

The settings contract already exists:

- `ASSET_STORAGE_BACKEND`
- `ASSET_PUBLIC_BASE_URL`
- `ASSET_LOCAL_ROOT`
- `ASSET_S3_BUCKET`
- `ASSET_S3_REGION`
- `ASSET_S3_ENDPOINT_URL`
- `ASSET_S3_ACCESS_KEY_ID`
- `ASSET_S3_SECRET_ACCESS_KEY`

Runtime implementation currently supports local only:

- `src/backend/features/generation_ai/asset_storage.py`

Production server is expected to run in Hetzner Nuremberg. Use Hetzner Object
Storage endpoint `https://nbg1.your-objectstorage.com` for production examples.

## Scope

- Add `S3GeneratedAssetStorage`.
- Use simple S3-compatible operations only:
  - put object
  - content type
  - optional metadata
- Keep `storage_key` as the canonical path.
- Keep `ASSET_PUBLIC_BASE_URL=/static/generated-assets` supported so old URLs remain stable.
- Serve `/static/generated-assets/<storage_key>` from Object Storage in the frontend when S3 is enabled.
- Validate required S3 config when `ASSET_STORAGE_BACKEND=s3`.
- Add dependency needed for S3 client usage.
- Update `.env.prod.example` and deployment docs with Hetzner Nuremberg example values.
- Do not migrate existing files in this task.

## Acceptance Checks

- `build_generated_asset_storage()` returns local or S3 storage based on settings.
- Missing S3 config fails fast with a clear error.
- `put_bytes()` normalizes keys and content-type extensions exactly like local storage.
- Returned `GeneratedAssetRef` includes `storage_backend="s3"`.
- Returned public URL is based on `ASSET_PUBLIC_BASE_URL`, not direct bucket URLs unless configured that way.
- The frontend can open the returned `/static/generated-assets/<storage_key>` URL from S3.
- Unit tests cover S3 calls with a fake/stub client.

## Handoff Prompt

```text
We are working in C:\install\projects\pets\TurnBasedMMORPG.

Read first:
- docs/agent-skills/turnbasedmmorpg-project/SKILL.md
- docs/agent-skills/turnbasedmmorpg-backend/SKILL.md
- docs/agent-skills/turnbasedmmorpg-deployment-management/SKILL.md
- docs/agent-skills/turnbasedmmorpg-testing-strategy/SKILL.md

Task:
Implement S3-backed generated asset storage for production. Local storage remains
the default. Use Hetzner Object Storage as an S3-compatible target, with
Nuremberg endpoint examples. Do not migrate existing production assets in this
task.

Relevant files:
- src/backend/features/generation_ai/asset_storage.py
- src/backend/config/settings.py
- tests/backend/features/generation_ai/test_asset_storage.py
- .env.prod.example
- docs/ru/management/deployment.md
- docs/ru/management/deployment-contract.md
- docs/planning/tasks/admin-content-ops/04-generated-asset-storage-s3.md

Rules:
- Keep storage_key canonical.
- Do not store direct Hetzner URLs as required canonical data.
- Do not make S3 mandatory for local development.
- Use simple S3-compatible put-object behavior only; avoid AWS-only advanced features.

Verification:
- Add unit tests with a fake S3 client or botocore Stubber.
- Run tests/backend/features/generation_ai with --no-cov.
- If deploy docs/env change, update the relevant changelog marker.
```
