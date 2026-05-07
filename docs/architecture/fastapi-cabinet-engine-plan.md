# FastAPI Cabinet Engine Plan

## Goal

Build a reusable admin cabinet engine inside this project first, then move it to a standalone FastAPI library with minimal rewriting.

The future-library code must live under:

```text
src/fastapi_cabinet/
```

Project-specific cabinet assembly and game integrations must live outside that package. The engine should not import `src.backend`, `src.frontend`, or game-specific `src.shared` modules.

## Core Idea

The engine behaves like a small FastAPI-friendly admin framework:

1. Feature packages may expose a local `cabinet.py`.
2. A project-level `cabinet.py` lists which cabinet files are enabled.
3. The library walks that list, imports the cabinet files, registers admin classes/modules, and builds header, sidebar, dashboard, widgets, and routes.
4. The FastAPI application only calls the library include function.

Preferred application shape:

```python
from fastapi_cabinet.fastapi import include_cabinet
from src.frontend.cabinet import CABINET_MODULES

include_cabinet(app, modules=CABINET_MODULES, mount_path="/cabinet")
```

Preferred project-level cabinet file:

```python
# src/frontend/cabinet.py

CABINET_MODULES = (
    "src.frontend.site_features.cabinet.modules.game_server.cabinet",
    "src.frontend.site_features.cabinet.modules.world.cabinet",
)
```

The first implementation can use explicit string paths. Later we can also support imported modules or callables.

## Design Rules

- Keep `src/fastapi_cabinet/` library-clean.
- Use Pydantic contracts where data crosses into rendering or route boundaries.
- Use simple dataclasses only for internal immutable declarations if Pydantic adds no value.
- Do not start with generic model CRUD.
- Do not start with a full settings subsystem.
- Treat settings pages as normal modules/widgets until patterns repeat.
- Treat resources as a later design topic; FastAPI/SQLAlchemy resources need a different design than Django `ModelForm`.
- Keep permissions as a contract from day one, but default implementation can be permissive/simple.

## Target File Layout

```text
src/fastapi_cabinet/
  __init__.py
  fastapi.py
  site.py
  registry.py
  loader.py
  runtime.py
  exceptions.py

  contracts/
    __init__.py
    admin.py
    navigation.py
    dashboard.py
    widgets.py
    layout.py
    permissions.py
    providers.py

  rendering/
    __init__.py
    layout_mapper.py
    widget_mapper.py
    service_mapper.py

  templates/
    cabinet/
      base.html
      dashboard.html
      module.html
      includes/
        header.html
        sidebar.html
        widget_frame.html
      widgets/
        metric.html
        table.html
        list.html

  static/
    css/
      cabinet.css
    js/
      cabinet.js
```

Project-specific assembly:

```text
src/frontend/cabinet.py
src/frontend/site_features/cabinet/
  modules/
    game_server/
      cabinet.py
      service.py
      mapper.py
```

## Public API Sketch

### `fastapi_cabinet.fastapi`

```python
from collections.abc import Sequence
from types import ModuleType

from fastapi import FastAPI

CabinetModuleRef = str | ModuleType

def include_cabinet(
    app: FastAPI,
    *,
    modules: Sequence[CabinetModuleRef],
    mount_path: str = "/cabinet",
    site: CabinetSite | None = None,
) -> CabinetSite:
    ...
```

Responsibilities:

- create or receive a `CabinetSite`;
- load all configured `cabinet.py` modules;
- build router from registry;
- include router into the FastAPI app;
- mount cabinet static assets under a non-conflicting path, for example `/cabinet/static`;
- return the site for tests/debugging.

### `fastapi_cabinet.site`

```python
class CabinetSite:
    def __init__(self) -> None:
        self.registry = CabinetRegistry()

    def register(self, admin: type[CabinetAdmin] | CabinetAdmin) -> None:
        ...

    def build_router(self, mount_path: str = "/cabinet") -> APIRouter:
        ...


cabinet_site = CabinetSite()
```

This gives a familiar admin style:

```python
from fastapi_cabinet import CabinetAdmin, cabinet_site

class WorldAdmin(CabinetAdmin):
    key = "world"
    label = "World"
    icon = "map"

cabinet_site.register(WorldAdmin)
```

Important: global `cabinet_site` is convenient, but `include_cabinet(..., site=...)` should support isolated test sites.

## Feature `cabinet.py` Contract

Simple feature file:

```python
# src/frontend/site_features/cabinet/modules/world/cabinet.py

from fastapi_cabinet import CabinetAdmin, MetricWidget, SidebarItem, cabinet_site


class WorldAdmin(CabinetAdmin):
    key = "world"
    label = "World"
    icon = "map"
    path = "/cabinet/world"

    sidebar = (
        SidebarItem(key="overview", label="Overview", path="/cabinet/world"),
        SidebarItem(key="biomes", label="Biomes", path="/cabinet/world/biomes"),
    )

    dashboard_widgets = (
        MetricWidget(
            key="world_nodes",
            title="World Nodes",
            provider="world.nodes_count",
        ),
    )


cabinet_site.register(WorldAdmin)
```

Advanced feature file:

```python
from fastapi_cabinet import CabinetRegistry


def register_cabinet(registry: CabinetRegistry) -> None:
    registry.add_module(...)
```

The loader should support both:

- modules that call `cabinet_site.register(...)` at import time;
- modules that expose `register_cabinet(registry)`.

The class-based API is the preferred path. The function hook is for unusual modules.

## Admin Class Contract

`CabinetAdmin` is the main developer experience layer.

```python
class CabinetAdmin:
    key: str
    label: str
    icon: str = ""
    path: str | None = None
    group: str = "main"
    order: int = 100

    sidebar: tuple[SidebarItem, ...] = ()
    dashboard_widgets: tuple[DashboardWidget, ...] = ()

    async def get_dashboard_context(self, request: Request) -> dict[str, object]:
        return {}

    async def get_sidebar_badges(self, request: Request) -> dict[str, int | str]:
        return {}
```

Meaning:

- class variables describe static cabinet structure;
- `get_dashboard_context()` is for module-specific extra context;
- `get_sidebar_badges()` is for counts/statuses shown near sidebar items;
- widget data should normally come from widget providers, not a giant page dict.

## Rendering Contracts

Use Pydantic models for the map passed to Jinja templates.

### Navigation

```python
from pydantic import BaseModel


class SidebarItem(BaseModel):
    key: str
    label: str
    path: str
    icon: str = ""
    badge_key: str | None = None
    order: int = 100
    permission: str | None = None


class HeaderItem(BaseModel):
    key: str
    label: str
    path: str
    icon: str = ""
    group: str = "main"
    order: int = 100
```

### Layout Map

```python
class CabinetLayoutMap(BaseModel):
    mount_path: str
    title: str
    active_module: str | None
    header: list[HeaderItem]
    sidebar: list[SidebarItem]
    sidebar_badges: dict[str, int | str] = {}
```

### Widget Maps

```python
class MetricWidgetMap(BaseModel):
    kind: str = "metric"
    key: str
    title: str
    value: str
    subtitle: str | None = None
    trend: str | None = None
    icon: str = ""


class TableColumnMap(BaseModel):
    key: str
    label: str
    align: str = "left"


class TableWidgetMap(BaseModel):
    kind: str = "table"
    key: str
    title: str
    columns: list[TableColumnMap]
    rows: list[dict[str, object]]
```

Templates should receive maps like these, not raw ORM objects or arbitrary service responses.

## Service Mapper Concept

Feature services can return domain data, backend API data, database rows, or Redis snapshots. The mapper converts that into cabinet template maps.

Flow:

```text
domain data / backend API response
  -> feature service
  -> feature mapper
  -> Pydantic render contract
  -> Jinja template
```

Example:

```python
class GameServerMapper:
    def online_players_metric(self, dto: OnlinePlayersDTO) -> MetricWidgetMap:
        return MetricWidgetMap(
            key="online_players",
            title="Online Players",
            value=str(dto.count),
            trend=f"+{dto.delta}" if dto.delta > 0 else str(dto.delta),
            icon="users",
        )
```

Provider example:

```python
async def online_players_provider(context: CabinetRequestContext) -> MetricWidgetMap:
    dto = await context.services.game_server.get_online_players()
    return GameServerMapper().online_players_metric(dto)
```

## Widget Provider Contract

`DashboardWidget` declarations should point to a provider key:

```python
MetricWidget(
    key="online_players",
    title="Online Players",
    provider="game_server.online_players",
)
```

Registry stores declarations. Runtime resolves providers.

Initial provider registration options:

1. Register providers on `CabinetAdmin`.
2. Register providers through `cabinet_site.provider(...)`.
3. Register providers inside `register_cabinet(registry)`.

Recommended first implementation:

```python
class GameServerAdmin(CabinetAdmin):
    providers = {
        "game_server.online_players": online_players_provider,
    }
```

This keeps module wiring local and avoids a large global providers dict.

## Loader Behavior

`loader.py` should:

1. Accept `Sequence[str | ModuleType]`.
2. Import string modules with `importlib.import_module`.
3. If module has `register_cabinet`, call it with the active registry.
4. Otherwise rely on import-time `cabinet_site.register(...)`.
5. Raise a clear error when import fails or the hook has the wrong shape.

Pseudo-code:

```python
def load_cabinet_modules(modules, site):
    for ref in modules:
        module = import_module(ref) if isinstance(ref, str) else ref
        hook = getattr(module, "register_cabinet", None)
        if hook is not None:
            hook(site.registry)
```

Open question for implementation: import-time registration must register against the same `site` used by `include_cabinet`. If global `cabinet_site` is used, `include_cabinet` should default to that global site.

## Runtime Resolver

`runtime.py` resolves request state:

- active module by path prefix;
- active sidebar item;
- layout map;
- user context;
- permission checks.

Initial resolver can be simple:

```text
request.url.path startswith module.path -> active module
```

Later it can support spaces, groups, nested modules, and custom route naming.

## Permission Contract

Start with a small protocol:

```python
class PermissionProvider(Protocol):
    async def can(self, request: Request, permission: str) -> bool:
        ...
```

Default:

```python
class AllowAllPermissionProvider:
    async def can(self, request, permission):
        return True
```

This lets us add real auth later without changing widget/module contracts.

## First Implementation Milestones

### Phase 1: Library skeleton

Files:

- `src/fastapi_cabinet/__init__.py`
- `src/fastapi_cabinet/fastapi.py`
- `src/fastapi_cabinet/site.py`
- `src/fastapi_cabinet/registry.py`
- `src/fastapi_cabinet/loader.py`
- `src/fastapi_cabinet/contracts/navigation.py`
- `src/fastapi_cabinet/contracts/admin.py`
- `src/fastapi_cabinet/contracts/widgets.py`

Deliverable:

- `include_cabinet(app, modules=...)` works.
- Feature `cabinet.py` can register a `CabinetAdmin`.
- Tests verify modules are loaded and registry contains expected modules.

### Phase 2: Dashboard and layout maps

Files:

- `src/fastapi_cabinet/runtime.py`
- `src/fastapi_cabinet/rendering/layout_mapper.py`
- `src/fastapi_cabinet/rendering/widget_mapper.py`
- `src/fastapi_cabinet/templates/cabinet/base.html`
- `src/fastapi_cabinet/templates/cabinet/dashboard.html`
- `src/fastapi_cabinet/templates/cabinet/widgets/metric.html`
- `src/fastapi_cabinet/templates/cabinet/widgets/table.html`
- `src/fastapi_cabinet/static/css/cabinet.css`

Deliverable:

- `/cabinet` renders a dashboard from registered modules.
- Header and sidebar are assembled from registry.
- Static assets are served under `/cabinet/static`.

### Phase 3: Provider and service mapper

Files:

- `src/fastapi_cabinet/contracts/providers.py`
- `src/fastapi_cabinet/rendering/service_mapper.py`
- project module example under `src/frontend/site_features/cabinet/modules/game_server/`

Deliverable:

- Widget providers can return Pydantic widget maps.
- A project module can map backend/game data into template maps.

### Phase 4: Project integration

Files:

- `src/frontend/cabinet.py`
- update `src/frontend/app.py` to call `include_cabinet`.
- add one sample project cabinet module.

Deliverable:

- Current frontend container serves the new cabinet path.
- Existing cabinet placeholder can be replaced or left unused.

### Phase 5: Later library features

Candidates after the first working cabinet:

- settings form contracts;
- resource descriptors;
- row/table actions;
- modal contracts;
- real permission provider;
- separate cabinet container;
- package extraction.

Do not build these until the base dashboard/admin flow proves useful.

## Testing Plan

Initial tests should live under:

```text
tests/fastapi_cabinet/
  test_loader.py
  test_registry.py
  test_admin_contract.py
  test_runtime.py
```

Project integration tests can live under:

```text
tests/frontend/site_features/cabinet/
```

Minimum checks:

- registering an admin class creates one module;
- module import calls `register_cabinet`;
- duplicate module keys fail clearly;
- layout mapper sorts header/sidebar by `order`;
- widget provider result validates against Pydantic contract;
- `/cabinet` returns 200 in a FastAPI test client.

## Open Decisions

- Should the public package name be `fastapi_cabinet` or `fast_api_cabinet`? Recommendation: `fastapi_cabinet`, matching the ecosystem spelling.
- Should feature `cabinet.py` use import-time `cabinet_site.register(...)`, explicit `register_cabinet(...)`, or both? Recommendation: support both, document class-based import-time style as the happy path.
- Should project cabinet modules live in backend features, frontend features, or a dedicated cabinet feature tree? Recommendation for this project: start under `src/frontend/site_features/cabinet/modules/` to preserve frontend/backend separation. Later, backend features can expose cabinet declarations only if those declarations avoid backend internals.
- Should providers call backend APIs or local services? For this project, cabinet running inside frontend should call backend HTTP APIs.
