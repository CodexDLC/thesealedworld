from src.backend.resources.game_data.feints.schemas import FeintConfigDTO

# ==========================================
# ГЛОБАЛЬНЫЕ РЕЕСТРЫ (In-Memory DB)
# ==========================================

FEINT_REGISTRY: dict[str, FeintConfigDTO] = {}


def _initialize_library() -> None:
    # TODO: Load definitions here
    pass


# ==========================================
# PUBLIC API
# ==========================================


def get_feint_config(feint_id: str) -> FeintConfigDTO | None:
    return FEINT_REGISTRY.get(feint_id)


def get_all_feints() -> list[FeintConfigDTO]:
    return list(FEINT_REGISTRY.values())


# Auto-init
_initialize_library()
