from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from tools.validators.items_resources import validate_items_resources
    from tools.validators.scenario_fixtures import validate_scenario_fixtures
    from tools.validators.skills_resources import validate_skills_resources

    errors: list[str] = []
    errors.extend(validate_items_resources(ROOT))
    errors.extend(validate_skills_resources(ROOT))
    errors.extend(validate_scenario_fixtures(ROOT))

    if errors:
        print("\nFixture validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Fixture validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
