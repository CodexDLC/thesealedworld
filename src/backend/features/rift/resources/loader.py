from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.backend.features.rift.dto import RiftPoolNodeDTO

_RESOURCE_DIR = Path(__file__).resolve().parent / "json"


class RiftResourceLoader:
    def __init__(self, resource_dir: Path = _RESOURCE_DIR) -> None:
        self.resource_dir = resource_dir

    def load_setting(self, setting_key: str) -> dict[str, Any]:
        return self._load_json(f"{setting_key}/master.json")

    def list_setting_keys(self) -> list[str]:
        return sorted(
            path.name for path in self.resource_dir.iterdir() if path.is_dir() and (path / "master.json").is_file()
        )

    def load_node_pool(self, setting_key: str) -> dict[str, RiftPoolNodeDTO]:
        raw = self._load_json(f"{setting_key}/nodes.json")
        nodes = [RiftPoolNodeDTO.model_validate(item) for item in raw.get("nodes", [])]
        return {node.pool_node_id: node for node in nodes}

    def load_scale_presets(self) -> dict[str, dict[str, Any]]:
        raw = self._load_json("rift_scale_presets.json")
        return self._index_presets(raw)

    def load_zone_assembly_presets(self) -> dict[str, dict[str, Any]]:
        raw = self._load_json("zone_assembly_presets.json")
        return self._index_presets(raw)

    def load_dev_character_snapshot(self, snapshot_key: str = "starter_rift") -> dict[str, Any]:
        return self._load_json(f"{snapshot_key}/dev_character.json")

    def _load_json(self, filename: str) -> dict[str, Any]:
        path = self.resource_dir / filename
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _index_presets(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
        presets = raw.get("presets", [])
        result: dict[str, dict[str, Any]] = {}
        for item in presets:
            if not isinstance(item, dict):
                continue
            preset_key = item.get("preset_key")
            if isinstance(preset_key, str) and preset_key:
                result[preset_key] = item
        return result
