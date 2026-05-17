from __future__ import annotations

# ruff: noqa: E402, I001

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from src.backend.features.monsters.scripts.regenerate_images import main  # noqa: E402


if __name__ == "__main__":
    main()
