from __future__ import annotations

from typing import Any

D4_LOCATION_MASTER_STYLE = (
    "ancient technomagical sacred architecture, black and white seamless monolith stone, "
    "faint ether-gold veins embedded in stone, ruined but majestic old capital, ritual engineering "
    "that looks like magic, solemn dark survival fantasy, painterly realistic game concept art"
)

D4_LOCATION_LORE_CONTEXT = (
    "Aur-Entar is the last capital of an ancient technomagical civilization. The Circle of Exodus is its preserved "
    "25-node inner sector around the Exodus portal plaza, still maintained by a planetary intelligence after the "
    "sealed world's collapse. Survivor additions are poor, temporary, and secondary: coarse cloth, rope, rough wood, "
    "small fires, and scavenged repairs kept near the edges of eternal monolith architecture."
)

D4_LOCATION_CAMERA_RULES = (
    "wide 16:9 browser RPG establishing shot of the location, not a directional point-of-view, "
    "show the node landmark clearly, readable open center area for UI overlays, darker side edges for interface panels, "
    "no close foreground subject, no action scene"
)

D4_LOCATION_NEGATIVE_PROMPT = (
    "no characters, no people, no silhouettes, no readable text, no letters, no numbers, no signs, no logo, "
    "no watermark, no UI, no modern buildings, no concrete, no asphalt, no cars, no guns, no cables, no power lines, "
    "no screens, no holograms, no sci-fi panels, no spaceship, no laboratory, no ordinary medieval castle as the main style, "
    "no village cottages, no anime, no cartoon, no blurry low detail, no pure black void"
)

ROLE_ADDONS: dict[str, str] = {
    "portal_plaza": (
        "huge circular ritual portal plaza, preserved central monolith platform, radial ether channels, "
        "broken ceremonial arches and obelisks, survivor camp only along the far edges"
    ),
    "trial_tower": (
        "windowless monolith trial tower beside a paved processional street, sealed arched entrance, "
        "subtle spatial distortion in the doorway, ancient arena threshold atmosphere"
    ),
    "shadow_quarter": (
        "narrow shadowed quarter of towering monolith facades, cold indirect light, deep doorways, "
        "clear central passage through oppressive ruins"
    ),
    "library_ruins": (
        "collapsed ancient library district, fallen monolith columns, stone shelves and archive slabs, "
        "fresh careful excavation traces kept secondary"
    ),
    "tavern_refuge": (
        "southern ancient reception pavilion and monolith street approach first, with the last refuge tavern only as a "
        "secondary occupied hall edge, warm dim light behind patched shutters, rough wood and cloth additions kept small"
    ),
    "blocked_quarter": (
        "blocked urban quarter, ancient warehouse thresholds buried under rubble and scavenged debris, "
        "rough barricade lines at the edges, usable center path"
    ),
    "artisan_quarter": (
        "ancient artisan district, dormant stone workbenches, cold ether tools and workshop arches, "
        "primitive repairs and small work shelters kept secondary"
    ),
    "elders_avenue": (
        "broad seamless monolith avenue, preserved civic hall and ancient armory frontage, "
        "primitive council and forge signs of occupation without readable text"
    ),
    "market_square": (
        "old eastern supply plaza inside the capital first, low monolith plinths and floor channels defining the space, "
        "with poor barter tables and torn cloth awnings as a secondary human layer"
    ),
    "inner_gate": (
        "massive inner ceremonial gate arch in a monolith wall, primitive wooden reinforcement, dead ancient mechanisms, "
        "controlled passage through the protected district"
    ),
    "barracks_plot": (
        "roofless ancient barracks foundation against the inner wall, intact monolith partitions, cleared protected plot, "
        "storage potential but empty of people"
    ),
    "stables_plot": (
        "ancient beast stables against the inner wall, stone stalls, empty wind-scoured pens, "
        "dead technomagical fittings shaped like ritual architecture"
    ),
    "warehouse_plot": (
        "cleared warehouse foundation near the inner wall, thick uncracked monolith backing, rubble pushed to the sides, "
        "protected empty buildable plot"
    ),
    "ancient_forge": (
        "ancient forge structure with a high stone chimney, dormant ether furnace, soot-dark monolith channels, "
        "primitive tools secondary and no modern machinery"
    ),
    "guardhouse_plot": (
        "small roofless guardhouse fused into the western inner wall, intact monolith walls, cleared floor, "
        "windscreened buildable niche"
    ),
    "armory_plot": (
        "empty fortified armory room in the wall, broken threshold, dust and old weapon racks implied by stone forms, "
        "no visible weapons in foreground"
    ),
    "trading_niches": (
        "row of carved trading niches in the eastern monolith wall, cleared stone alcoves, small awnings and tables, "
        "foundation-like usable spaces"
    ),
    "broken_shrine": (
        "broken semicircular shrine foundation, fallen statue base, faded ether-carved reliefs without readable symbols, "
        "quiet buildable place beside the wall"
    ),
    "bastion": (
        "massive corner bastion of the inner citadel wall, thick monolith geometry, broken parapets, "
        "cleared protected interior suitable as a future stronghold"
    ),
}

TAG_ADDONS: dict[str, str] = {
    "active_portal": "subtle active portal glow and stable ether light, restrained and sacred",
    "runic_circle": "circular non-readable geometric channels in the floor, not letters",
    "tents": "small poor tents only at the edges",
    "tavern": "warm refuge lights and patched wooden shutters",
    "market": "torn awnings, barter tables, baskets and cloth bundles, no people",
    "forge": "dormant furnace, soot, ether-gold channels",
    "chapel": "broken shrine geometry, altar-like stone, no religious text",
    "bastion": "thick corner-wall mass and high defensive geometry",
    "gate": "large ceremonial arch and controlled passage",
    "inner_wall": "monolithic inner wall edge, ancient defensive scale",
    "dark_alley": "deep shadows and narrow vertical sightlines",
    "overgrowth": "limited moss and creeping plants, secondary to monolith stone",
    "buildable_plot": "cleared empty foundation with usable central space",
    "wood_patch": "rough scavenged wood repairs contrasted against eternal stone",
}


def build_d4_capital_hub_prompt(payload: dict[str, Any]) -> str:
    visual_overrides = _safe_dict(payload.get("visual_overrides"))
    tags = [str(tag) for tag in payload.get("environment_tags") or payload.get("tags") or [] if str(tag).strip()]
    node_role = str(visual_overrides.get("node_role") or payload.get("node_role") or _infer_node_role(payload, tags))
    role_addon = ROLE_ADDONS.get(node_role, ROLE_ADDONS["portal_plaza"] if "hub_center" in tags else "")
    tag_addons = [TAG_ADDONS[tag] for tag in tags if tag in TAG_ADDONS]
    composition = str(visual_overrides.get("composition") or "").strip()
    forbidden = [str(item) for item in visual_overrides.get("forbidden") or [] if str(item).strip()]

    sections = [
        f"MASTER_STYLE: {D4_LOCATION_MASTER_STYLE}.",
        f"LORE_CONTEXT: {D4_LOCATION_LORE_CONTEXT}",
        f"LOCATION: {payload.get('loc_id') or payload.get('id')} - {payload.get('title')}.",
        f"PLAYER_TEXT_CONTEXT: {payload.get('description') or ''}",
        f"CAMERA_AND_UI: {D4_LOCATION_CAMERA_RULES}.",
    ]
    if role_addon:
        sections.append(f"NODE_ROLE ({node_role}): {role_addon}.")
    if composition:
        sections.append(f"COMPOSITION: {composition}.")
    if tag_addons:
        sections.append(f"TAG_DETAILS: {'; '.join(dict.fromkeys(tag_addons))}.")
    if forbidden:
        sections.append(f"LOCAL_FORBIDDEN: {', '.join(forbidden)}.")
    sections.append(f"NEGATIVE_PROMPT: {D4_LOCATION_NEGATIVE_PROMPT}.")
    sections.append("OUTPUT: single clean environment background, no markdown, no captions.")
    return "\n".join(sections)


def _infer_node_role(payload: dict[str, Any], tags: list[str]) -> str:
    title = str(payload.get("title") or "").lower()
    tag_set = set(tags)
    if "hub_center" in tag_set or "runic_circle" in tag_set:
        return "portal_plaza"
    if "market" in tag_set:
        return "market_square"
    if "tavern" in tag_set:
        return "tavern_refuge"
    if "ancient_tower" in tag_set or "arena" in tag_set:
        return "trial_tower"
    if "dark_alley" in tag_set:
        return "shadow_quarter"
    if "ancient_knowledge" in tag_set:
        return "library_ruins"
    if "gate" in tag_set:
        return "inner_gate"
    if "bastion" in tag_set:
        return "bastion"
    if "forge" in tag_set:
        return "ancient_forge"
    if "chapel" in tag_set:
        return "broken_shrine"
    if "warehouse" in tag_set:
        return "warehouse_plot"
    if "armory" in tag_set:
        return "armory_plot"
    if "guardhouse" in tag_set:
        return "guardhouse_plot"
    if "stable" in tag_set:
        return "stables_plot"
    if "barracks" in tag_set:
        return "barracks_plot"
    if "market_stall" in tag_set:
        return "trading_niches"
    if "workshop" in tag_set:
        return "artisan_quarter"
    if "barrels" in tag_set or "завал" in title:
        return "blocked_quarter"
    if "town_hall" in tag_set or "blacksmith" in tag_set:
        return "elders_avenue"
    return "blocked_quarter" if "buildable_plot" in tag_set else "portal_plaza"


def _safe_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
