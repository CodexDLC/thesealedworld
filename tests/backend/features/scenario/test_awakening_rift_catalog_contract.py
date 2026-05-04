import json
from pathlib import Path
from typing import Any

from src.backend.features.game_catalog.skills.services import SkillCatalogService
from src.backend.features.items.dto.instance import ItemGenerationRequestDTO
from src.backend.features.items.runtime.item_factory import ItemFactory
from src.backend.features.items.services.catalog_service import ItemCatalogService

QUEST_DIR = (
    Path(__file__).resolve().parents[4]
    / "src"
    / "backend"
    / "features"
    / "scenario"
    / "resources"
    / "json"
    / "awakening_rift"
)


def test_awakening_rift_reward_items_exist_in_item_catalog() -> None:
    item_catalog = ItemCatalogService.load_default()
    item_factory = ItemFactory(item_catalog)

    missing = sorted(item_id for item_id in _collect_reward_values("loot_queue") if item_id not in item_catalog.base_items)

    assert missing == []
    for item_id in _collect_reward_values("loot_queue"):
        item = item_factory.generate(ItemGenerationRequestDTO(base_id=item_id, source="scenario:awakening_rift"))
        assert item.base_id == item_id


def test_awakening_rift_reward_skills_exist_in_skill_catalog() -> None:
    skill_catalog = SkillCatalogService()

    missing = sorted(skill_key for skill_key in _collect_reward_values("skills_queue") if skill_catalog.get(skill_key) is None)

    assert missing == []


def _collect_reward_values(queue_key: str) -> set[str]:
    values: set[str] = set()
    for path in sorted((QUEST_DIR / "nodes").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        _walk(data, queue_key, values)
    return values


def _walk(value: Any, queue_key: str, values: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == queue_key:
                values.update(_parse_queue_value(child))
            else:
                _walk(child, queue_key, values)
    elif isinstance(value, list):
        for child in value:
            _walk(child, queue_key, values)


def _parse_queue_value(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_strip_push(value)}
    if isinstance(value, list):
        return {_strip_push(item) for item in value if isinstance(item, str)}
    return set()


def _strip_push(value: str) -> str:
    return value.removeprefix("push:")
