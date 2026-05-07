from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from src.backend.features.character.resources import CHARACTER_ATTRIBUTE_TEXT
from src.backend.features.items.services import ItemCatalogService
from src.shared.schemas import ScenarioButtonDTO, ScenarioPayloadDTO
from src.shared.schemas.panel import PanelDTO, PanelWidgetDTO

VISIBLE_PROFILE_ORDER = [
    "agility",
    "projection",
    "endurance",
    "intellect",
    "prediction",
    "mental",
    "perception",
    "strength",
    "memory",
]

if TYPE_CHECKING:
    from src.backend.features.scenario.engine.director import ScenarioDirector


class ScenarioFormatter:
    _item_titles: dict[str, str] | None = None

    def __init__(self, director: ScenarioDirector) -> None:
        self.director = director
        self.tag_pattern = re.compile(r"\[#(?:stats:)?([\w.]+)\]")
        self.bare_queue_pattern = re.compile(r"(?<![#\w])loot_queue\.(\d+)\b")

    def render_payload(
        self,
        node: dict[str, Any],
        context: dict[str, Any],
        master: dict[str, Any],
    ) -> ScenarioPayloadDTO:
        actions = self.director.get_available_actions(node, context)

        # Use system_messages from node if present
        system_alerts = node.get("system_messages", [])
        ui = self.resolve_ui(node, master)
        right_panel = self.build_right_panel(node, context, master)

        return ScenarioPayloadDTO(
            node_key=node.get("node_key", "unknown"),
            node_type=node.get("node_type", "event"),
            phase=node.get("phase"),
            speaker=node.get("speaker"),
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
                    icon=self.resolve_action_icon(action["payload"]),
                )
                for action in actions
            ],
            is_terminal=bool(node.get("is_terminal", False)),
            ui=ui,
            extra_data={
                "quest_title": master.get("display_name", "UNKNOWN_QUEST"),
                "node_type": node.get("node_type", "event"),
                "phase": node.get("phase"),
                "speaker": node.get("speaker"),
                "ui": ui,
                "background_url": node.get("background_url") or master.get("background_url"),
                "show_left_sidebar": self.resolve_sidebar_visibility(
                    node,
                    master,
                    "show_left_sidebar",
                    ui.get("left_panel"),
                ),
                "show_right_sidebar": self.resolve_sidebar_visibility(
                    node,
                    master,
                    "show_right_sidebar",
                    right_panel.widgets,
                ),
                "left_panel": ui.get("left_panel", {}),
                "right_panel": right_panel.model_dump(mode="json"),
                "rewards": node.get("rewards", []),
                "flags": node.get("flags", []),
                **context,
            },
        )

    @staticmethod
    def resolve_action_icon(action: dict[str, Any]) -> str:
        explicit_icon = action.get("icon")
        if explicit_icon and explicit_icon != "default":
            return str(explicit_icon)

        math = action.get("math") or {}
        positive_keys = {
            key
            for key, value in math.items()
            if isinstance(key, str) and key != "step_counter" and str(value).strip().startswith("+")
        }
        label = str(action.get("label", "")).lower()

        if "w_strength" in positive_keys:
            return "strength"
        if "w_agility" in positive_keys:
            return "move"
        if "w_intellect" in positive_keys or "w_perception" in positive_keys:
            return "inspect"
        if "w_memory" in positive_keys:
            return "brain"
        if "w_endurance" in positive_keys or "w_mental" in positive_keys:
            return "guard"
        if "warning" in label or "предупреж" in label or "плам" in label or "огн" in label:
            return "risk"
        if any(key.startswith("t_fire") or key.startswith("t_dark") for key in positive_keys):
            return "risk"
        if "w_prediction" in positive_keys:
            return "question"
        return "default"

    @staticmethod
    def resolve_sidebar_visibility(
        node: dict[str, Any],
        master: dict[str, Any],
        key: str,
        fallback: Any,
    ) -> bool:
        node_value = node.get(key)
        if node_value is not None:
            return bool(node_value)
        master_value = master.get(key)
        if master_value is not None:
            return bool(master_value)
        return bool(fallback)

    def format_text(self, text: Any, context: dict[str, Any]) -> str:
        if not text:
            return ""

        # Handle case where label might be a dict (as suggested by the user)
        if isinstance(text, dict):
            text = text.get("text", str(text))

        if not isinstance(text, str):
            text = str(text)

        # 1. First, replace standard context tags like [#stats.w_memory]
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
            return self._display_value(key, value)

        formatted = self.tag_pattern.sub(replace_tag, text)
        formatted = self.bare_queue_pattern.sub(
            lambda match: self._display_queue_item("loot_queue", match.group(1), context), formatted
        )

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

    def _display_queue_item(self, queue_key: str, index_text: str, context: dict[str, Any]) -> str:
        queue = context.get(queue_key)
        if not isinstance(queue, list):
            return f"Unknown:{queue_key}.{index_text}"
        index = int(index_text)
        if not 0 <= index < len(queue):
            return f"Unknown:{queue_key}.{index_text}"
        return self._display_value(f"{queue_key}.{index_text}", queue[index])

    def _display_value(self, key: str, value: Any) -> str:
        if key.startswith("loot_queue.") and isinstance(value, str):
            return self._item_title(value)
        return str(value)

    @classmethod
    def _item_title(cls, item_id: str) -> str:
        if cls._item_titles is None:
            cls._item_titles = {
                key: str(value.get("title") or key)
                for key, value in ItemCatalogService.load_default().all_public_text().items()
            }
        return cls._item_titles.get(item_id, item_id)

    @staticmethod
    def resolve_ui(node: dict[str, Any], master: dict[str, Any]) -> dict[str, Any]:
        ui = dict(master.get("ui") or {})
        node_ui = node.get("ui") or {}
        for key, value in node_ui.items():
            if isinstance(value, dict) and isinstance(ui.get(key), dict):
                ui[key] = {**ui[key], **value}
            else:
                ui[key] = value
        return ui

    @staticmethod
    def build_status_bar(master: dict[str, Any], context: dict[str, Any]) -> list[str]:
        return [
            f"{field.get('label', '')} {context.get(field.get('key'), '??')}"
            for field in master.get("status_bar_fields", [])
        ]

    @staticmethod
    def build_right_panel(node: dict[str, Any], context: dict[str, Any], master: dict[str, Any]) -> PanelDTO:
        order_index = {name: index for index, name in enumerate(VISIBLE_PROFILE_ORDER)}
        raw_weights = [
            (key[2:], value)
            for key, value in sorted(
                context.items(),
                key=lambda item: (
                    -item[1] if item[0].startswith("w_") and isinstance(item[1], int | float) else 0,
                    order_index.get(item[0][2:], len(order_index)),
                ),
            )
            if key.startswith("w_") and isinstance(value, int | float) and value > 0
        ]
        total_weight = sum(float(value) for _, value in raw_weights)
        weights = [
            {
                "label": CHARACTER_ATTRIBUTE_TEXT.get(attr_key, {}).get("title_en", attr_key.upper()),
                "value": value,
                "display_value": f"{round(float(value) / total_weight * 100):d}%" if total_weight else "0%",
                "percent": round(float(value) / total_weight * 100, 2) if total_weight else 0,
                "catalog": "attributes",
                "catalog_key": attr_key,
            }
            for attr_key, value in raw_weights
        ]
        loot_queue = [
            {"label": value, "catalog": "items", "catalog_key": value}
            for value in context.get("loot_queue", [])
            if isinstance(value, str)
        ]
        skills_queue = [
            {"label": value, "catalog": "skills", "catalog_key": value}
            for value in context.get("skills_queue", [])
            if isinstance(value, str)
        ]

        widgets: list[PanelWidgetDTO] = [
            PanelWidgetDTO(
                type="key_value",
                title="SCENARIO",
                items=[
                    {"key": "Quest", "value": master.get("display_name", context.get("quest_key", "UNKNOWN"))},
                    {"key": "Node", "value": node.get("node_key", context.get("current_node_key", "unknown"))},
                    {"key": "Step", "value": context.get("step_counter", 0)},
                ],
            ),
            PanelWidgetDTO(
                type="meter_list",
                title="CHOICE PROFILE",
                data={"max": 20},
                items=weights,
                visible=bool(weights),
            ),
            PanelWidgetDTO(type="list", title="PENDING GEAR", items=loot_queue, visible=bool(loot_queue)),
            PanelWidgetDTO(type="list", title="PENDING SKILLS", items=skills_queue, visible=bool(skills_queue)),
        ]

        if node.get("system_messages"):
            widgets.append(
                PanelWidgetDTO(
                    type="list",
                    title="SYSTEM",
                    items=[{"label": message} for message in node.get("system_messages", [])],
                )
            )

        return PanelDTO(id="scenario_right", title="SCENARIO_TRACE", widgets=widgets)
