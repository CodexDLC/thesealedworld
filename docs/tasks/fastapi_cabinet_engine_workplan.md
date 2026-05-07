# FastAPI Cabinet Engine Workplan

Source architecture document: [FastAPI Cabinet Engine Plan](../architecture/fastapi-cabinet-engine-plan.md).

This checklist tracks implementation of the reusable `fastapi_cabinet` engine inside the current project before extraction to a standalone library.

## Phase 0: Decisions And Boundaries

- [x] Confirm public package name: `fastapi_cabinet`.
- [x] Confirm first runtime target: current frontend FastAPI app.
- [x] Confirm first cabinet mount path: `/cabinet`.
- [x] Confirm static mount path: `/cabinet/static`.
- [x] Keep `src/fastapi_cabinet/` free of imports from `src.backend`, `src.frontend`, and game-specific `src.shared`.
- [x] Treat generic resources/model CRUD as a later phase.
- [x] Treat settings as normal modules/widgets for the first implementation.

## Phase 1: Library Skeleton

- [x] Create `src/fastapi_cabinet/__init__.py`.
- [x] Create `src/fastapi_cabinet/exceptions.py`.
- [x] Create `src/fastapi_cabinet/site.py`.
- [x] Create `src/fastapi_cabinet/registry.py`.
- [x] Create `src/fastapi_cabinet/loader.py`.
- [x] Create `src/fastapi_cabinet/fastapi.py`.
- [x] Export primary public API from `src/fastapi_cabinet/__init__.py`.
- [x] Add isolated tests under `tests/fastapi_cabinet/`.

Acceptance:

- [x] `include_cabinet(app, modules=...)` exists.
- [x] `CabinetSite` exists.
- [x] `cabinet_site` exists.
- [x] `CabinetRegistry` stores registered modules.
- [x] duplicate module keys fail with a clear exception.

## Phase 2: Core Contracts

- [x] Create `src/fastapi_cabinet/contracts/__init__.py`.
- [x] Create `src/fastapi_cabinet/contracts/admin.py`.
- [x] Create `src/fastapi_cabinet/contracts/navigation.py`.
- [x] Create `src/fastapi_cabinet/contracts/widgets.py`.
- [x] Create `src/fastapi_cabinet/contracts/layout.py`.
- [x] Create `src/fastapi_cabinet/contracts/permissions.py`.
- [x] Create `src/fastapi_cabinet/contracts/providers.py`.

Acceptance:

- [x] `CabinetAdmin` supports class variables: `key`, `label`, `icon`, `path`, `group`, `order`.
- [x] `CabinetAdmin` supports `sidebar` and `dashboard_widgets`.
- [x] `CabinetAdmin.get_dashboard_context(request)` exists.
- [x] `CabinetAdmin.get_sidebar_badges(request)` exists.
- [x] Navigation contracts validate through Pydantic.
- [x] Widget render maps validate through Pydantic.
- [x] Permission provider protocol exists with permissive default.

## Phase 3: Cabinet Module Loading

- [x] Support string module refs in `loader.py`.
- [x] Support imported module refs in `loader.py`.
- [x] Support `register_cabinet(registry)` hook.
- [x] Support import-time `cabinet_site.register(AdminClass)` style.
- [x] Add clear errors for missing modules.
- [x] Add clear errors for invalid hooks.

Acceptance:

- [x] A feature-local `cabinet.py` can register one `CabinetAdmin`.
- [x] A project-level `CABINET_MODULES` tuple can load multiple cabinet modules.
- [x] Tests cover string import loading.
- [x] Tests cover explicit `register_cabinet` loading.

## Phase 4: Router And Runtime

- [x] Create `src/fastapi_cabinet/runtime.py`.
- [x] Implement active module resolution from request path.
- [x] Implement dashboard route for `/cabinet`.
- [x] Implement module route support for registered module paths.
- [x] Add FastAPI router building in `CabinetSite.build_router()`.
- [x] Wire `include_cabinet(app, modules=..., mount_path=...)`.

Acceptance:

- [x] `/cabinet` returns 200 in a FastAPI test client.
- [x] active module is resolved by path prefix.
- [x] empty registry renders a useful empty state or fails with a clear setup error.

## Phase 5: Rendering Layer

- [x] Create `src/fastapi_cabinet/rendering/__init__.py`.
- [x] Create `src/fastapi_cabinet/rendering/layout_mapper.py`.
- [x] Create `src/fastapi_cabinet/rendering/widget_mapper.py`.
- [x] Create `src/fastapi_cabinet/rendering/service_mapper.py`.
- [x] Create base Jinja template `src/fastapi_cabinet/templates/cabinet/base.html`.
- [x] Create dashboard template `src/fastapi_cabinet/templates/cabinet/dashboard.html`.
- [x] Create module template `src/fastapi_cabinet/templates/cabinet/module.html`.
- [x] Create includes for header/sidebar/widget frame.
- [x] Create initial CSS at `src/fastapi_cabinet/static/css/cabinet.css`.

Acceptance:

- [x] Header is built from registered admins.
- [x] Sidebar is built from active admin.
- [x] Sidebar badges are rendered from `get_sidebar_badges()`.
- [x] Layout map is Pydantic-validated before rendering.
- [x] Templates do not receive raw ORM objects.

## Phase 6: Dashboard Widgets

- [x] Implement metric widget declaration.
- [x] Implement table widget declaration.
- [x] Implement list widget declaration.
- [x] Implement provider lookup.
- [x] Implement async provider execution.
- [x] Implement provider result validation.
- [x] Create templates for metric/table/list widgets.

Acceptance:

- [x] `dashboard_widgets` on `CabinetAdmin` render on `/cabinet`.
- [x] provider key resolves to async callable.
- [x] bad provider key fails clearly.
- [x] provider output validates against widget map contracts.

## Phase 7: Project-Level Integration

- [x] Create `src/frontend/cabinet.py`.
- [x] Define `CABINET_MODULES`.
- [x] Include cabinet in `src/frontend/app.py`.
- [x] Add first project cabinet module under `src/frontend/site_features/cabinet/modules/`.
- [x] Keep existing placeholder route either removed or made non-conflicting.
- [x] Ensure frontend auth/cookie behavior still works for `/cabinet`.

Acceptance:

- [x] Current frontend app serves the new engine-backed cabinet.
- [x] Existing site/game routes still work.
- [x] No backend internals are imported by `src/fastapi_cabinet/`.

## Phase 8: First Real Module

- [x] Choose first module: recommended `game_server`.
- [x] Create feature `cabinet.py`.
- [x] Create feature service.
- [x] Create feature mapper.
- [x] Add one metric widget.
- [x] Add one table or list widget.
- [x] Add focused tests for mapper/provider.

Acceptance:

- [x] The first module proves the full flow: cabinet file -> registry -> provider -> mapper -> widget template.
- [x] Module code calls backend through an integration/client boundary if it needs project data.

## Phase 9: Quality Gate

- [x] Add tests for `tests/fastapi_cabinet/`.
- [x] Add tests for project cabinet integration.
- [x] Run targeted tests for the new package.
- [ ] Run the strongest practical project gate before declaring implementation complete.

Commands to consider:

```powershell
uv run pytest tests/fastapi_cabinet tests/frontend/site_features/cabinet --no-cov
uv run python tools/dev/check.py
```

## Later Phases

- [ ] Real permission provider wired to project auth.
- [ ] Settings form contracts.
- [ ] Resource descriptors.
- [ ] Table row actions.
- [ ] Modal contracts.
- [ ] Separate cabinet container.
- [ ] Extract `src/fastapi_cabinet/` into standalone package.
