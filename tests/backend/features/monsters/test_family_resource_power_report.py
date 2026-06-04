import pytest

from tools.monsters import family_resource_power_report


def test_family_resource_power_report_is_disabled_for_replacement_only_contract() -> None:
    with pytest.raises(RuntimeError, match="replacement-only storage contract"):
        family_resource_power_report.main()
