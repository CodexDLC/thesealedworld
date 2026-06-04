import pytest

from tools.monsters import rebuild_generated_monsters


def test_rebuild_generated_monsters_tool_is_disabled_for_replacement_only_contract() -> None:
    with pytest.raises(RuntimeError, match="replacement-only storage contract"):
        rebuild_generated_monsters.main()
