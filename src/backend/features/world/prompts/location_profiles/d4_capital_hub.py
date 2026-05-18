from __future__ import annotations

from typing import Any

D4_LOCATION_MASTER_STYLE = (
    "ancient technomagical sacred architecture, black and white seamless monolith stone, "
    "weathered dark-grey and white stone surfaces, faint ether-gold veins embedded in stone, overcast cool lighting, "
    "ruined but majestic old capital, ritual engineering "
    "that looks like magic, solemn dark survival fantasy, painterly realistic game concept art"
)

D4_LOCATION_LORE_CONTEXT = (
    "Aur-Entar is the last capital of an ancient technomagical civilization. The Circle of Exodus is its preserved "
    "25-node inner sector around the Exodus portal plaza, held together by ancient city systems and residual ritual "
    "engineering after the sealed world's collapse. These are blocks of the former elite city center, not caves, rooms, "
    "or a separate village: streets, plazas, wall-side yards, ceremonial facades, and service pockets of a high-status "
    "capital district. Survivor additions are visible and readable as services, but they are built into the ancient "
    "place instead of replacing it: coarse cloth, rope, rough wood, small fires, barter tables, patched shutters, and "
    "scavenged repairs attached to eternal monolith architecture."
)

D4_LOCATION_TEXT_CONTRACT = (
    "The player-facing text is layered: first paragraph describes the location identity and ancient architecture; "
    "a following paragraph may describe a service or human use installed inside that location. The image must follow "
    "the same contract: show the ancient location as the primary subject, and make the service layer visible enough "
    "to read as a tavern, market, gate checkpoint, camp, workshop, or future build plot when tags imply it. If the "
    "player text says street, quarter, square, yard, or wall-side plot, use that place type as the main frame of the "
    "scene; do not reduce it to a small isolated object."
)

D4_SETTLEMENT_PROGRESS_CONTRACT = (
    "Service nodes are already equipped and may visibly show a tavern, market, checkpoint, arena entrance, council "
    "hall, or other installed use. Empty buildable nodes are different: they should read as plazas, quarters, wall-side "
    "yards, or old foundations that players can claim later. Show lot boundaries, cleared squares, blocked thresholds, "
    "rubble piles, stacked beams, survey stakes, canvas covers, and repair materials, but do not make every buildable "
    "node look like a finished house or finished shop."
)

D4_TACTICAL_SERIES_CONTRACT = (
    "Treat each output as one adjacent tactical location cell from the same city grid, not as a standalone postcard. "
    "Use an elevated 3/4 tactical location background with the same camera height, same scale, same wall material, "
    "same lighting, and same ruin density across a batch. The image should read as a playable RPG location cell with "
    "a clear landmark, readable floor plane, and visible neighboring-boundary logic, while still being painterly "
    "environment art rather than a diagram. Each cell is a small urban quarter or street segment, not a 10-meter room: "
    "show enough ground, wall length, side structures, and open circulation space to feel like a place players can "
    "move through and later build around. Preserve the v7 readable exits and quarter scale, but keep one continuous "
    "ancient eastern-wall style across the whole set."
)

D4_WALL_STYLE_CONTRACT = (
    "The eastern wall must remain one continuous elite-district monolith boundary across the series: weathered dark "
    "grey and black-white seamless stone, restrained pale highlights, faint ether-gold cracks, massive non-medieval "
    "ritual-engineering geometry. Do not change it into bright sunlit limestone, a clean white castle, a normal "
    "fortress wall, or a different architectural set between cells."
)

D4_LOCATION_CAMERA_RULES = (
    "wide 16:9 browser RPG tactical establishing shot of the location, slightly elevated 3/4 camera, "
    "not a first-person directional point-of-view, show the node landmark clearly, readable open center area for UI "
    "overlays, darker side edges for interface panels, no close foreground subject, no doorway/tunnel framing, "
    "no action scene"
)

D4_GROUND_PLANE_RULES = (
    "The image must have a readable walkable ground plane: paved plaza, street, yard, foundation floor, threshold "
    "surface, or claimable lot grid where future player construction could happen. Use elevated 3/4 tactical depth, "
    "but keep it as real environment perspective, not a flat map, board-game tile, floating platform, balcony-only "
    "view, empty abyss foreground, or cliff-edge scene. Corner bastions need an accessible inner yard inside the wall "
    "turn, not only a wall-top or tower roof. Do not frame the location as a tiny enclosed room; include a street or "
    "quarter-sized ground area below the landmark."
)

D4_LOCATION_NEGATIVE_PROMPT = (
    "no characters, no people, no silhouettes, no readable text, no letters, no numbers, no signs, no logo, "
    "no watermark, no UI, no modern buildings, no concrete, no asphalt, no cars, no guns, no cables, no power lines, "
    "no screens, no holograms, no sci-fi panels, no spaceship, no laboratory, no ordinary medieval castle as the main style, "
    "no separate village as the main subject, no anime, no cartoon, no blurry low detail, no pure black void, "
    "no black side bars, no letterbox masks, no flat top-down map, no board-game tile view, no floating platform, "
    "no empty abyss as main foreground, no balcony-only view, no tiny enclosed room, no cinematic wall close-up, "
    "no sealed arena, no foreground doorway frame, no bright sunlit white fortress, no limestone castle wall, "
    "no readable glyph panels, no pseudo writing"
)

ROLE_ADDONS: dict[str, str] = {
    "portal_plaza": (
        "huge circular ritual portal plaza, preserved central monolith platform, radial ether channels, "
        "broken ceremonial arches and obelisks, survivor camp visibly present along the rim as a service layer"
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
        "southern ancient reception pavilion and monolith street approach first, with the last refuge tavern clearly "
        "readable as an occupied warm hall built into one side of the pavilion, patched shutters, rough wood, cloth, "
        "and firelight continuing the location instead of becoming a separate inn"
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
        "with poor barter tables, baskets, crates, and torn cloth awnings visibly using those ancient plinths"
    ),
    "inner_gate": (
        "massive inner ceremonial gate arch in a monolith wall, primitive wooden reinforcement, dead ancient mechanisms, "
        "controlled passage through the protected district with a visible checkpoint layer but no guards"
    ),
    "barracks_plot": (
        "roofless ancient barracks foundation against the inner wall, intact monolith partitions, several claimable rooms "
        "or lots in different states, some cleared square floors and some blocked by rubble, no finished house as the focus"
    ),
    "stables_plot": (
        "ancient beast stables against the inner wall, stone stalls and wind-scoured pens, a few cleared claimable bays "
        "with stacked timber and canvas, other bays still blocked by old debris"
    ),
    "warehouse_plot": (
        "warehouse quarter near the inner wall, thick uncracked monolith backing, rubble pushed into piles, visible lot "
        "edges, cleared foundations and stored beams waiting for player construction"
    ),
    "ancient_forge": (
        "ancient forge structure with a high stone chimney, dormant ether furnace, soot-dark monolith channels, "
        "primitive tools secondary and no modern machinery"
    ),
    "guardhouse_plot": (
        "small roofless guardhouse fused into the western inner wall, intact monolith walls, cleared floor, windscreened "
        "buildable niche with survey stakes and stacked repair materials, nearby debris showing more work remains"
    ),
    "armory_plot": (
        "fortified armory shell inside the wall, broken threshold, old rack-like stone forms, claimable interior spaces, "
        "some storage materials staged while other corners remain dusty and blocked"
    ),
    "trading_niches": (
        "row of carved trading niches in the eastern monolith wall, several small claimable alcoves, one or two already "
        "converted into rough stalls with awnings and tables, other niches still empty or half-cleared"
    ),
    "broken_shrine": (
        "broken semicircular shrine foundation beside the wall, fallen statue base, faded ether-carved reliefs without "
        "readable symbols, a quiet buildable lot with survey stakes, rubble piles, and cleared square floors"
    ),
    "bastion": (
        "massive corner bastion of the inner citadel wall with the wall visibly turning around the corner, thick "
        "monolith geometry, broken parapets, protected interior divided into claimable yard spaces, some rubble not yet "
        "cleared, some stacked materials, and open square lots for future player building, plus at least one visible "
        "street exit continuing into the adjacent elite district, not a sealed symmetrical arena"
    ),
}

TAG_ADDONS: dict[str, str] = {
    "active_portal": "subtle active portal glow and stable ether light, restrained and sacred",
    "runic_circle": "circular non-readable geometric channels in the floor, not letters",
    "tents": "poor tents and camp gear visible as a readable service layer at the edges",
    "tavern": "warm refuge lights, patched wooden shutters, rough counter forms, and cloth additions inside ancient stone",
    "market": "torn awnings, barter tables, baskets, crates, and cloth bundles, no people",
    "forge": "dormant furnace, soot, ether-gold channels",
    "chapel": "broken shrine geometry, altar-like stone, no religious text",
    "bastion": "thick corner-wall mass and high defensive geometry",
    "gate": "large ceremonial arch and controlled passage",
    "inner_wall": "monolithic inner wall edge, ancient defensive scale",
    "dark_alley": "deep shadows and narrow vertical sightlines",
    "overgrowth": "limited moss and creeping plants, secondary to monolith stone",
    "buildable_plot": (
        "player-claimable open plot states: rubble piles, cleared foundations, visible lot edges, stacked beams, canvas "
        "covers, survey stakes, and unfinished square floors for future construction"
    ),
    "camp": "small occupied camp layer with storage, canvas, fire pits, and repair materials",
    "wood_patch": "rough scavenged wood repairs contrasted against eternal stone as a visible human layer",
}


def build_d4_capital_hub_prompt(payload: dict[str, Any]) -> str:
    visual_overrides = _safe_dict(payload.get("visual_overrides"))
    tags = [str(tag) for tag in payload.get("environment_tags") or payload.get("tags") or [] if str(tag).strip()]
    node_role = str(visual_overrides.get("node_role") or payload.get("node_role") or _infer_node_role(payload, tags))
    role_addon = ROLE_ADDONS.get(node_role, ROLE_ADDONS["portal_plaza"] if "hub_center" in tags else "")
    tag_addons = [TAG_ADDONS[tag] for tag in tags if tag in TAG_ADDONS]
    composition = str(visual_overrides.get("composition") or "").strip()
    directional_context = _build_directional_context(payload)
    forbidden = [str(item) for item in visual_overrides.get("forbidden") or [] if str(item).strip()]

    sections = [
        f"MASTER_STYLE: {D4_LOCATION_MASTER_STYLE}.",
        f"LORE_CONTEXT: {D4_LOCATION_LORE_CONTEXT}",
        f"LOCATION_TEXT_LAYER_CONTRACT: {D4_LOCATION_TEXT_CONTRACT}",
        f"SETTLEMENT_PROGRESS_CONTRACT: {D4_SETTLEMENT_PROGRESS_CONTRACT}",
        f"TACTICAL_SERIES_CONTRACT: {D4_TACTICAL_SERIES_CONTRACT}",
        f"WALL_STYLE_CONTRACT: {D4_WALL_STYLE_CONTRACT}",
        f"LOCATION: {payload.get('loc_id') or payload.get('id')} - {payload.get('title')}.",
        f"PLAYER_TEXT_CONTEXT: {payload.get('description') or ''}",
        f"CAMERA_AND_UI: {D4_LOCATION_CAMERA_RULES}.",
        f"GROUND_PLANE: {D4_GROUND_PLANE_RULES}",
    ]
    if directional_context:
        sections.append(f"MAP_SERIES_DIRECTION: {directional_context}.")
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


def _build_directional_context(payload: dict[str, Any]) -> str:
    loc_id = str(payload.get("loc_id") or payload.get("id") or "")
    try:
        x_raw, y_raw = loc_id.split("_", 1)
        x = int(x_raw)
        y = int(y_raw)
    except ValueError:
        return ""
    if x == 54:
        series_prefix = (
            "EAST_WALL_SERIES: these five images are adjacent tactical location cells along the same eastern inner "
            "wall of Aur-Entar; keep the same city, same wall material, same lighting, same camera height, same scale, "
            "and same ruin density; the eastern monolith wall is the shared boundary across the series; every cell "
            "must include the street, yard, or quarter below the wall, not only a close-up of the wall itself; preserve "
            "readable exits and district continuation, while avoiding bright sunlit white wall style"
        )
        if y == 50:
            return (
                f"{series_prefix}; cell 54_50 is the northeast corner bastion where two wall lines meet, with the "
                "eastern wall turning into the northern wall, claimable yard spaces inside the corner, and a visible "
                "street exit continuing along the northern elite district"
            )
        if y == 54:
            return (
                f"{series_prefix}; cell 54_54 is the southeast corner bastion where the eastern wall turns into the "
                "southern wall, with limited overgrowth, claimable yard spaces inside the corner, and a visible street "
                "exit continuing along the southern elite district"
            )
        if y == 52:
            return (
                f"{series_prefix}; cell 54_52 is the east gate through the shared wall, with the gate as the main "
                "landmark and the interior supply plaza opening toward the left or center"
            )
        if y == 51:
            return (
                f"{series_prefix}; cell 54_51 is a wall-niche and barracks-plot cell, with carved alcoves and several "
                "claimable bays in different states of clearing along the shared eastern wall"
            )
        return (
            f"{series_prefix}; cell 54_53 is a shrine plot against the shared eastern wall, with a broken semicircular "
            "foundation, survey stakes, and some cleared square floors for future building"
        )
    return ""


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
