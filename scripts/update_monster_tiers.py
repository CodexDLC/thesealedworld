import re
from pathlib import Path

FAMILIES_DIR = Path("src/backend/features/monsters/resources/families")
files = ["bandits.py", "goblins.py", "rats.py", "wolves.py"]

for filename in files:
    filepath = FAMILIES_DIR / filename
    if not filepath.exists():
        print(f"File {filepath} not found!")
        continue

    content = filepath.read_text(encoding="utf-8")

    # Replace min_tier: X with min_tier: 0
    content = re.sub(r'"min_tier":\s*\d+', '"min_tier": 0', content)
    # Replace max_tier: Y with max_tier: 5
    content = re.sub(r'"max_tier":\s*\d+', '"max_tier": 5', content)

    filepath.write_text(content, encoding="utf-8")
    print(f"Updated {filename}")
