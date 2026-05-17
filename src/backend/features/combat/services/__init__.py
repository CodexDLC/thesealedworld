__all__ = ["CombatAnalyticsDashboardService", "CombatLifecycleService", "CombatSessionService"]


def __getattr__(name: str):
    if name == "CombatAnalyticsDashboardService":
        from src.backend.features.combat.services.analytics_dashboard_service import CombatAnalyticsDashboardService

        return CombatAnalyticsDashboardService
    if name == "CombatLifecycleService":
        from src.backend.features.combat.services.lifecycle_service import CombatLifecycleService

        return CombatLifecycleService
    if name == "CombatSessionService":
        from src.backend.features.combat.services.session_service import CombatSessionService

        return CombatSessionService
    raise AttributeError(name)
