from src.frontend.game_features.game_menu.view_models.menu import GameMenuItemVM, GameMenuVM
from src.shared.enums.domain import CoreDomain


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
        return GameMenuVM(center=GameMenuItemVM(id="scenario", label="SCENARIO", icon="chat", url="#", is_active=True))

    def _build_exploration_menu(self) -> GameMenuVM:
        return GameMenuVM(
            l2=GameMenuItemVM(id="inventory", label="BAG", icon="inventory", url="/game/inventory"),
            l1=GameMenuItemVM(id="skills", label="SKILLS", icon="bolt", url="/game/skills"),
            center=GameMenuItemVM(id="explore", label="WORLD", icon="map", url="/game/explore", is_active=True),
            r1=GameMenuItemVM(id="quests", label="QUESTS", icon="journal", url="/game/quests"),
            r2=GameMenuItemVM(id="character", label="CHAR", icon="person", url="/game/character"),
        )

    def _build_combat_menu(self) -> GameMenuVM:
        # Placeholder for combat menu
        return GameMenuVM(center=GameMenuItemVM(id="combat", label="BATTLE", icon="swords", url="#", is_active=True))
