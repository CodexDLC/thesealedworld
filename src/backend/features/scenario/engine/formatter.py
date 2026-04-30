from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from src.shared.schemas import ScenarioButtonDTO, ScenarioPayloadDTO

if TYPE_CHECKING:
    from src.backend.features.scenario.engine.director import ScenarioDirector


class ScenarioFormatter:
    def __init__(self, director: ScenarioDirector) -> None:
        self.director = director
        self.tag_pattern = re.compile(r"\[#(?:stats:)?([\w.]+)\]")

    def render_payload(
        self,
        node: dict[str, Any],
        context: dict[str, Any],
        master: dict[str, Any],
    ) -> ScenarioPayloadDTO:
        actions = self.director.get_available_actions(node, context)

        # Use system_messages from node if present
        system_alerts = node.get("system_messages", [])

        return ScenarioPayloadDTO(
            node_key=node.get("node_key", "unknown"),
            display_name=node.get("display_name") or master.get("display_name"),
            icon=node.get("icon"),
            avatar=node.get("avatar") or master.get("default_avatar"),
            text=self.format_text(node.get("text", node.get("text_content", "")), context),
            alerts=system_alerts,
            status_bar=self.build_status_bar(master, context),
            buttons=[
                ScenarioButtonDTO(
                    label=self.format_text(action["label"], context),
                    action_id=action["action_id"],
                    icon=action["payload"].get("icon"),
                )
                for action in actions
            ],
            is_terminal=bool(node.get("is_terminal", False)),
            extra_data={
                "quest_title": master.get("display_name", "UNKNOWN_QUEST"),
                "rewards": node.get("rewards", []),
                "flags": node.get("flags", []),
                **context,
            },
        )

    def format_text(self, text: str, context: dict[str, Any]) -> str:
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            value: Any = context
            for part in key.split("."):
                if isinstance(value, dict):
                    value = value.get(part)
                elif isinstance(value, list) and part.isdigit():
                    index = int(part)
                    value = value[index] if 0 <= index < len(value) else None
                else:
                    value = None
                if value is None:
                    return f"Unknown:{key}"
            return str(value)

        return self.tag_pattern.sub(replace, text or "")

    @staticmethod
    def build_status_bar(master: dict[str, Any], context: dict[str, Any]) -> list[str]:
        return [
            f"{field.get('label', '')} {context.get(field.get('key'), '??')}"
            for field in master.get("status_bar_fields", [])
        ]
