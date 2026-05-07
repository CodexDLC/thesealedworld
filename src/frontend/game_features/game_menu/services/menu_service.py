from src.frontend.game_features.game_menu.view_models.menu import GameMenuItemVM, GameMenuVM
from src.shared.enums import CoreDomain


class GameMenuService:
    """
    Orchestrates the game menu state based on the current game domain.
    Can be expanded to fetch additional data (e.g. notifications) if needed.
    """

    def build_menu(self, domain: CoreDomain) -> GameMenuVM:
        if domain == CoreDomain.SCENARIO:
            return self._build_scenario_menu()
        elif domain == CoreDomain.EXPLORATION:
            return self._build_exploration_menu()
        elif domain == CoreDomain.COMBAT:
            return self._build_combat_menu()

        # Default empty menu for other states (Lobby, Onboarding, etc.)
        return GameMenuVM()

    def _build_scenario_menu(self) -> GameMenuVM:
        return GameMenuVM(
            l2=GameMenuItemVM(id="status", label="STATUS", icon="person", url="#", panel="left", panel_view="status"),
            l1=GameMenuItemVM(id="empty-left", label="", icon=None, url="#", is_disabled=True),
            center=GameMenuItemVM(id="scenario", label="SCENARIO", icon="talk", url="#", is_active=True),
            r1=GameMenuItemVM(id="trace", label="TRACE", icon="journal", url="#", panel="right", panel_view="context"),
            r2=GameMenuItemVM(id="empty-right", label="", icon=None, url="#", is_disabled=True),
        )

    def _build_exploration_menu(self) -> GameMenuVM:
        return GameMenuVM(
            l2=GameMenuItemVM(id="status", label="STATUS", icon="person", url="#", panel="left", panel_view="status"),
            l1=GameMenuItemVM(id="builds", label="BUILDS", icon="bolt", url="#", panel="left", panel_view="builds"),
            center=GameMenuItemVM(id="explore", label="EXPLORE", icon="map", url="#", is_active=True),
            r1=GameMenuItemVM(id="inventory", label="INVENTORY", icon="inventory", url="#", window="inventory"),
            r2=GameMenuItemVM(id="view", label="VIEW", icon="journal", url="#", panel="right", panel_view="context"),
        )

    def _build_combat_menu(self) -> GameMenuVM:
        return GameMenuVM(
            l2=GameMenuItemVM(id="status", label="STATUS", icon="person", url="#", is_disabled=True),
            l1=GameMenuItemVM(id="builds", label="BUILDS", icon="bolt", url="#", is_disabled=True),
            center=GameMenuItemVM(id="combat", label="COMBAT", icon="swords", url="#", is_active=True),
            r1=GameMenuItemVM(id="inventory", label="INVENTORY", icon="inventory", url="#", is_disabled=True),
            r2=GameMenuItemVM(id="view", label="VIEW", icon="journal", url="#", is_disabled=True),
        )
