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
            display_name=node.get("display_name")
            or node.get("metadata", {}).get("location")
            or master.get("display_name"),
            icon=node.get("icon"),
            avatar=node.get("avatar") or master.get("default_avatar"),
            text=self.format_text(node.get("text", node.get("text_content", "")), context),
            system_messages=system_alerts,
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
                "background_url": node.get("background_url") or master.get("background_url"),
                "show_left_sidebar": node.get("show_left_sidebar", master.get("show_left_sidebar", True)),
                "show_right_sidebar": node.get("show_right_sidebar", master.get("show_right_sidebar", True)),
                "rewards": node.get("rewards", []),
                "flags": node.get("flags", []),
                **context,
            },
        )

    def format_text(self, text: Any, context: dict[str, Any]) -> str:
        if not text:
            return ""

        # Handle case where label might be a dict (as suggested by the user)
        if isinstance(text, dict):
            text = text.get("text", str(text))

        if not isinstance(text, str):
            text = str(text)

        # 1. First, replace standard context tags like [#stats.w_wisdom]
        def replace_tag(match: re.Match[str]) -> str:
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
                    # If it's a special UI tag like sys_actor, we handle it later
                    if key in ["sys_actor", "p_loc"]:
                        return match.group(0)
                    return f"Unknown:{key}"
            return str(value)

        formatted = self.tag_pattern.sub(replace_tag, text)

        # 2. Handle special UI prefixes (Space Rangers style)
        # Convert [#sys_actor]: MESSAGE to <div class="whisper">MESSAGE</div>
        if "[#sys_actor]:" in formatted:
            formatted = formatted.replace("[#sys_actor]:", '<div class="whisper">', 1) + "</div>"

        # 3. Simple color/style tags support (Space Rangers style)
        # {gold}text{/gold} -> <span class="col-accent">text</span>
        # {red}text{/red} -> <span class="col-danger">text</span>
        replacements = {
            "{gold}": '<span style="color: var(--col-accent);">',
            "{/gold}": "</span>",
            "{red}": '<span style="color: var(--col-danger);">',
            "{/red}": "</span>",
            "{cyan}": '<span style="color: var(--col-info);">',
            "{/cyan}": "</span>",
            "{green}": '<span style="color: var(--col-success);">',
            "{/green}": "</span>",
            "\n": "<br>",
        }
        for tag, html in replacements.items():
            formatted = formatted.replace(tag, html)

        return formatted

    @staticmethod
    def build_status_bar(master: dict[str, Any], context: dict[str, Any]) -> list[str]:
        return [
            f"{field.get('label', '')} {context.get(field.get('key'), '??')}"
            for field in master.get("status_bar_fields", [])
        ]
