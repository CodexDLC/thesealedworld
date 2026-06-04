import pytest

from tools.monsters import backfill_gear_score


def test_backfill_gear_score_tool_is_disabled_for_replacement_only_contract() -> None:
    with pytest.raises(RuntimeError, match="replacement-only storage contract"):
        backfill_gear_score.main()
