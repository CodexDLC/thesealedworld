from typing import Any, Protocol


class MenuDiscoveryProvider(Protocol):
    """
    Contract for retrieving the list of menu buttons.
    Implemented by FeatureDiscoveryService.
    """

    def get_menu_buttons(self, is_admin: bool | None = None) -> dict[str, dict[str, Any]]:
        """
        Returns menu configurations with optional admin filtering.
        """
        ...
