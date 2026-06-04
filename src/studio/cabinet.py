"""Studio cabinet module registry.

Mirrors `src/frontend/cabinet.py::CABINET_MODULES`. Each entry is the dotted
import path of a `*.cabinet` module that registers a `CabinetAdmin` subclass
into the global `cabinet_site` at import time.

This tuple starts empty in the infrastructure-prep PR. Analytical modules
(`site_analytics`, `player_analytics`, `combat`, `combat_ai_testing`,
`scenario`, `exploration`, `content_ops`) are appended one-by-one as they
migrate out of `src/frontend/features/cabinet/modules/` per the migration plan
(see `C:/Users/prime/.claude/plans/iterative-sleeping-thunder.md`).
"""

CABINET_MODULES: tuple[str, ...] = (
    # Контент (тяжёлые выборки монстров + примет)
    "src.studio.features.cabinet.modules.content_ops.cabinet",
)
