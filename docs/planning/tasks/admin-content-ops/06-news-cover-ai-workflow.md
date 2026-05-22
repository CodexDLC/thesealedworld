# Task 06 - News Cover AI Workflow

## Implementation Status

- [x] News cover prompt builder added for title/preview/status/body excerpt.
- [x] Backend news cover image task type and admin generation endpoint added.
- [x] Cabinet generate/preview/approve/reject flow added to news management.
- [x] Covered with prompt/task/cabinet workflow unit tests; no real AI provider call.
- [ ] Real AI cover generation smoke test pending provider credentials/runtime.

## Goal

Add a cabinet workflow to generate, preview, approve, and attach cover images to
news articles.

## Context

Existing news surfaces include:

- `src/frontend/features/cabinet/modules/news_management/cabinet.py`
- `src/frontend/features/news/`
- `src/frontend/templates/site/news/`
- `src/frontend/static/images/news/`

News is site-owned, but image generation should reuse the generated asset
storage contract so production can store approved covers in S3.

## Scope

- Add a news cover generation action in the existing news cabinet module.
- Build an image prompt from article title, preview, tags/status, and body excerpt.
- Generate an image through backend/generation-ai or an agreed site-to-game/internal API boundary.
- Show a preview before attaching it to the news article.
- Add explicit approve/reject actions.
- Store approved cover URL on the news article.
- Use storage keys under a stable namespace, for example:
  - `news/covers/<article_slug>/<asset_hash>.webp`
- Do not publish unapproved generated images automatically.

## Acceptance Checks

- Admin can request a cover image for a draft/news article.
- Admin sees the generated preview before applying it.
- Rejecting a preview leaves the article unchanged.
- Approving a preview updates the article cover image.
- Cover generation uses the generated asset storage abstraction.
- Tests cover prompt building, approve/reject behavior, and storage metadata.

## Handoff Prompt

```text
We are working in C:\install\projects\pets\TurnBasedMMORPG.

Read first:
- docs/agent-skills/turnbasedmmorpg-project/SKILL.md
- docs/agent-skills/turnbasedmmorpg-frontend/SKILL.md
- docs/agent-skills/turnbasedmmorpg-cabinet-design/SKILL.md
- docs/agent-skills/turnbasedmmorpg-backend/SKILL.md
- docs/agent-skills/turnbasedmmorpg-testing-strategy/SKILL.md

Task:
Add an admin news cover generation workflow. Admins should generate an image
prompt from article content, preview the generated cover, approve or reject it,
and only then attach it to the news article. Use the generated asset storage
contract for image bytes.

Relevant files:
- src/frontend/features/cabinet/modules/news_management/cabinet.py
- src/frontend/features/news/
- src/frontend/templates/site/news/
- src/frontend/static/images/news/
- src/backend/features/generation_ai/
- src/backend/core/ai.py
- docs/planning/tasks/admin-content-ops/06-news-cover-ai-workflow.md

Rules:
- News remains site/cabinet-owned.
- Image bytes should use the generated asset storage abstraction.
- Do not auto-publish generated covers without explicit approval.
- Do not store direct provider URLs as canonical article cover data.

Verification:
- Add tests for prompt generation and approve/reject behavior.
- Use fakes for AI/image generation in tests.
- Verify news list/detail templates render approved generated covers.
```
