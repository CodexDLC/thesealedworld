# tests/backend/features/exploration/test_navigation.py
import pytest
from src.backend.features.exploration.runtime.navigation import NavigationEngine
from src.shared.schemas.exploration import NavigationGridDTO

def test_navigation_grid_generation():
    current_loc = "50_50"
    exits = {
        "nav:50_49": {"time_duration": 1.0},  # North
        "nav:50_51": {"time_duration": 1.0},  # South
        "nav:49_50": {"time_duration": 1.0},  # West
        "nav:51_50": {"time_duration": 1.0},  # East
        "svc:shop": {"text_button": "Store"}
    }
    flags = {"is_safe_zone": True, "threat_tier": 0}
    
    grid = NavigationEngine.build_grid(current_loc, exits, flags)
    
    assert isinstance(grid, NavigationGridDTO)
    # Check directions
    assert grid.n.is_active is True
    assert "move:50_49" in grid.n.action
    assert grid.s.is_active is True
    assert "move:50_51" in grid.s.action
    
    # Check center
    assert grid.center.id == "look"
    
    # Check services
    assert len(grid.services) == 1
    assert grid.services[0].label == "🚪 Store"

def test_navigation_grid_with_walls():
    current_loc = "50_50"
    exits = {
        "nav:50_49": {"time_duration": 1.0},  # North only
    }
    flags = {}
    
    grid = NavigationEngine.build_grid(current_loc, exits, flags)
    
    assert grid.n.is_active is True
    assert grid.s.is_active is False
    assert grid.s.label == "⛔️"
