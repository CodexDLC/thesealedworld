from enum import StrEnum


class CoreDomain(StrEnum):
    LOBBY = "LOBBY"
    ONBOARDING = "ONBOARDING"
    EXPLORATION = "EXPLORATION"
    SCENARIO = "SCENARIO"
    COMBAT = "COMBAT"
    INVENTORY = "INVENTORY"
    GAME_MENU = "GAME_MENU"
    ARENA = "ARENA"
