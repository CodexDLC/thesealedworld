# Admin Content Ops Task Pack

This folder tracks the admin/cabinet content operations work needed before S3
generated asset storage becomes useful in production.

## Goal

Build an operational cabinet area for database/content moderation workflows:
generated monsters, generated images, news covers, and future asset migration.
The first milestone is read-only visibility. Mutation actions such as image
regeneration and S3 backfill come after the data can be inspected safely.

## Files

- `01-cabinet-section.md` - create the Content Ops / Database Moderation cabinet section.
- `02-monster-family-browser.md` - read-only generated monster family and member browser.
- `03-monster-visual-regeneration.md` - regenerate family and member images from the cabinet.
- `04-generated-asset-storage-s3.md` - add S3-backed generated asset storage.
- `05-prod-asset-backfill.md` - copy existing production generated assets into S3.
- `06-news-cover-ai-workflow.md` - generate and approve news cover images from news content.

## Sequencing

Recommended order:

1. Cabinet section shell.
2. Monster family browser.
3. Monster visual regeneration on local storage.
4. S3 storage implementation.
5. Production asset backfill.
6. News cover generation workflow.

S3 should not be the first task. It becomes valuable when the cabinet can
trigger and inspect regeneration safely.

## Current Local Status

- [x] Tasks 01-06 have local code and unit-test coverage in `codex/admin-content-ops`.
- [x] No AI provider, production server, push, or commit was used during local implementation.
- [x] `uv.lock` updated for the S3 dependency.
- [x] Hetzner Object Storage configured locally and single smoke upload verified.
- [ ] Tomorrow: run AI image smoke for monster/news cover and production backfill dry-run.

## Ownership

- Frontend/cabinet UI belongs to `src/frontend/features/cabinet/modules/`.
- Frontend must call backend through typed clients under `src/frontend/integrations/backend_api/`.
- Monster generation data and image regeneration belong to backend monsters/generation-ai features.
- News content and news cover approval are site/cabinet workflows, but generated image bytes should reuse the shared generated asset storage contract.

## Non-Goals

- Do not build a generic unsafe raw database editor as the first milestone.
- Do not store direct Hetzner Object Storage URLs as canonical data.
- Do not regenerate existing production images as the migration strategy.
- Do not make S3 mandatory for local development.
