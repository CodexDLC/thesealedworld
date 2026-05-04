"""
Конфигурация географии мира: Якоря, Палитры биомов и Статика.
Источники данных для генерации тегов.
"""

from typing import TypedDict

# Если Python < 3.11, NotRequired нужно импортировать из typing_extensions
# Если Python >= 3.11, можно из typing
try:
    from typing import NotRequired
except ImportError:
    # Заглушка для старых версий, чтобы код не падал,
    # но линтер может всё равно ругаться на отсутствие ключей.
    # Лучше установить: pip install typing_extensions
    from typing import NotRequired

# ==============================================================================
# 1. ГЛОБАЛЬНЫЕ КОНСТАНТЫ
# ==============================================================================
WORLD_WIDTH = 105
WORLD_HEIGHT = 105
REGION_SIZE = 15  # Размер Региона (15x15)
ZONE_SIZE = 5  # Размер Локации внутри Региона (5x5)

# Центр Хаба (D4)
HUB_CENTER = {"x": 52, "y": 52}

# Маппинг рядов для ID (A1..G7)
REGION_ROWS = ["A", "B", "C", "D", "E", "F", "G"]


# ==============================================================================
# 2. ОПРЕДЕЛЕНИЕ БИОМОВ (BIOME PALETTES)
# ==============================================================================


class TerrainMeta(TypedDict):
    """
    Строгая схема данных для тайла.
    NotRequired помечает ключи, которых может не быть в словаре.
    """

    # Обязательные поля (есть у всех)
    spawn_weight: int
    travel_cost: float
    is_passable: bool
    visual_tags: list[str]
    danger_mod: float

    # Новые поля (теперь они обязательны, так как есть везде в конфиге)
    role: str  # "background" | "echo" | "landmark"
    narrative_hint: str  # Описание для ЛЛМ

    # Опциональные поля (есть только у некоторых)
    is_unique: NotRequired[bool]  # Только для landmarks
    service_key: NotRequired[str]  # Только для активных точек


# ------------------------
# Обновлённый BIOME_DEFINITIONS (расширенный)
# ------------------------
BIOME_DEFINITIONS: dict[str, dict[str, TerrainMeta]] = {
    # --- 1. FOREST (Лес) ---
    "forest": {
        "heartwoods": {
            "spawn_weight": 30,
            "travel_cost": 1.5,
            "is_passable": True,
            "visual_tags": ["old_trees", "dense_roots", "dim_light"],
            "danger_mod": 1.4,
            "role": "background",
            "narrative_hint": "Густая, древняя часть леса; фон для локальных сцен.",
        },
        "grove": {
            "spawn_weight": 20,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["thin_trees", "soft_moss", "filtered_light"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Тихая роща с мягким мхом под ногами.",
        },
        "overgrowth": {
            "spawn_weight": 20,
            "travel_cost": 1.8,
            "is_passable": True,
            "visual_tags": ["vines", "thick_bushes", "tangled_branches"],
            "danger_mod": 1.3,
            "role": "background",
            "narrative_hint": "Заросший участок, мешающий передвижению и видимости.",
        },
        "clearwood": {
            "spawn_weight": 15,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["open_patch", "wildflowers", "scattered_trees"],
            "danger_mod": 0.8,
            "role": "background",
            "narrative_hint": "Небольшая поляна — пауза в густой чащобе.",
        },
        "fallen_wood": {
            "spawn_weight": 15,
            "travel_cost": 1.6,
            "is_passable": True,
            "visual_tags": ["broken_logs", "rotting_stumps", "fungus_spots"],
            "danger_mod": 1.2,
            "role": "background",
            "narrative_hint": "Места с поваленными стволами и гнилью.",
        },
        "forest_path": {
            "spawn_weight": 0,
            "travel_cost": 0.9,
            "is_passable": True,
            "visual_tags": ["trampled_ground", "narrow_trail", "bent_grass"],
            "danger_mod": 0.9,
            "role": "background",
            "narrative_hint": "Тропа — линейный элемент навигации внутри леса.",
        },
        # ECHO (лore-объекты)
        "echo_old_statuette": {
            "spawn_weight": 5,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["mossy_statuette", "carved_face", "half_buried"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Маленькая реликвия — след древних культов.",
        },
        "echo_ruined_waystone": {
            "spawn_weight": 6,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["crumbled_stone", "faded_glyphs", "lichen_strip"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Остатки указателя или камня пути древних.",
        },
        # LANDMARKS (доминианты)
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["stone_arch", "dormant_energy", "runic_circle"],
            "danger_mod": 1.6,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Древние врата, ожидающие активации.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["reality_tear", "unstable_air", "purple_haze"],
            "danger_mod": 1.8,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Здесь пространство истончилось — потенциальный разлом.",
        },
    },
    # --- 2. SWAMP (Болото) ---
    "swamp": {
        "shallow_mire": {
            "spawn_weight": 30,
            "travel_cost": 2.0,
            "is_passable": True,
            "visual_tags": ["muddy_water", "tall_reeds", "slow_current"],
            "danger_mod": 1.3,
            "role": "background",
            "narrative_hint": "Промежуточный участок топи, часто сырой и скользкий.",
        },
        "peat_isle": {
            "spawn_weight": 20,
            "travel_cost": 1.5,
            "is_passable": True,
            "visual_tags": ["dry_patch", "rotting_plants", "low_mist"],
            "danger_mod": 1.2,
            "role": "background",
            "narrative_hint": "Сухой островок среди болота, редкая твердая почва.",
        },
        "sinking_bog": {
            "spawn_weight": 15,
            "travel_cost": 3.0,
            "is_passable": True,
            "visual_tags": ["soft_ground", "dark_pools", "air_bubbles"],
            "danger_mod": 1.8,
            "role": "background",
            "narrative_hint": "Опасный участок — земля коварно прогибается под ногами.",
        },
        "reed_wall": {
            "spawn_weight": 20,
            "travel_cost": 2.2,
            "is_passable": True,
            "visual_tags": ["dense_reeds", "hissing_wind", "hidden_paths"],
            "danger_mod": 1.4,
            "role": "background",
            "narrative_hint": "Плотная полоса тростника, скрывающая проходы.",
        },
        "gator_pass": {
            "spawn_weight": 15,
            "travel_cost": 2.5,
            "is_passable": True,
            "visual_tags": ["murky_depths", "wet_tracks", "silent_shore"],
            "danger_mod": 1.6,
            "role": "background",
            "narrative_hint": "Группы глубоких луж и темных прибрежных зон.",
        },
        "wooden_planks": {
            "spawn_weight": 0,
            "travel_cost": 1.3,
            "is_passable": True,
            "visual_tags": ["old_boards", "creaking_steps", "shallow_path"],
            "danger_mod": 1.1,
            "role": "background",
            "narrative_hint": "Мостки и настилы через болотные участки.",
        },
        "echo_bog_shrine": {
            "spawn_weight": 6,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["waterlogged_altar", "rotted_carvings", "reed_crown"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Мёртвый алтарь — след религиозных практик древности.",
        },
        "echo_submerged_engine": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["rusted_gear", "half_submerged", "pipe_spurting"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Полузатонувший механизм — отпечаток промышленного прошлого.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 1.4,
            "is_passable": True,
            "visual_tags": ["mossy_arch", "stagnant_runic_pool", "root_wrapped"],
            "danger_mod": 1.7,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Врата, частично поглощённые болотной жизнью.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 1.6,
            "is_passable": True,
            "visual_tags": ["bubbling_void", "sour_mist", "floating_lichen"],
            "danger_mod": 1.9,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "В этом водоёме временами просверливаются трещины реальности.",
        },
    },
    # --- 3. WASTELAND (Пустошь) ---
    "wasteland": {
        "dust_field": {
            "spawn_weight": 30,
            "travel_cost": 1.1,
            "is_passable": True,
            "visual_tags": ["dry_dust", "flat_ground", "faint_haze"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Открытые, выжженные участки пустоши.",
        },
        "stone_plate": {
            "spawn_weight": 20,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["bare_rock", "heat_shimmer", "cracked_surface"],
            "danger_mod": 1.1,
            "role": "background",
            "narrative_hint": "Голая каменная плита — ровная, но беспощадная.",
        },
        "sand_stretch": {
            "spawn_weight": 20,
            "travel_cost": 1.3,
            "is_passable": True,
            "visual_tags": ["fine_sand", "soft_dunes", "wind_marks"],
            "danger_mod": 1.2,
            "role": "background",
            "narrative_hint": "Песчаные полосы — зыбкие и прячущие следы.",
        },
        "hardstep": {
            "spawn_weight": 15,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["packed_dirt", "dry_grass", "open_view"],
            "danger_mod": 0.9,
            "role": "background",
            "narrative_hint": "Твёрдый участок, по которому комфортнее двигаться.",
        },
        "ruined_ground": {
            "spawn_weight": 15,
            "travel_cost": 1.4,
            "is_passable": True,
            "visual_tags": ["collapsed_debris", "broken_tiles", "old_tracks"],
            "danger_mod": 1.3,
            "role": "background",
            "narrative_hint": "Осколки разрушений — следы прошлых построек.",
        },
        "old_road": {
            "spawn_weight": 0,
            "travel_cost": 0.8,
            "is_passable": True,
            "visual_tags": ["faded_marks", "broken_asphalt", "straight_line"],
            "danger_mod": 0.8,
            "role": "background",
            "narrative_hint": "Фрагменты старой магистрали.",
        },
        "echo_buried_mech": {
            "spawn_weight": 6,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["rusted_giant_robot", "half_buried", "ancient_war_machine"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Половина металлического титана, ушедшего под землю.",
        },
        "echo_shattered_highway": {
            "spawn_weight": 6,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["broken_asphalt", "faded_lines", "rusted_cars"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Рельеф старого шоссе — след индустриальной катастрофы.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["stone_pillars", "ashen_circle", "faint_runes"],
            "danger_mod": 1.6,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Врата, окружённые полупепельной равниной.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["air_rend", "dust_vortex", "violet_glow"],
            "danger_mod": 1.9,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Пульсирующий разрыв в тканях реальности.",
        },
    },
    # --- 4. MEADOW (Луг) ---
    "meadow": {
        "flower_plain": {
            "spawn_weight": 30,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["wildflowers", "soft_breeze", "tall_grass"],
            "danger_mod": 0.8,
            "role": "background",
            "narrative_hint": "Светлая поляна с цветами и мелкой фауной.",
        },
        "shepherd_slope": {
            "spawn_weight": 20,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["rolling_hill", "short_grass", "warm_ground"],
            "danger_mod": 0.9,
            "role": "background",
            "narrative_hint": "Пологий склон, часто используемый в прошлом для выпаса.",
        },
        "dew_lowland": {
            "spawn_weight": 20,
            "travel_cost": 1.1,
            "is_passable": True,
            "visual_tags": ["fresh_dew", "thin_streams", "cold_grass"],
            "danger_mod": 0.9,
            "role": "background",
            "narrative_hint": "Низина с росой и мелкими ручьями.",
        },
        "pasture_edge": {
            "spawn_weight": 15,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["broken_fence", "flat_field", "light_wind"],
            "danger_mod": 0.8,
            "role": "background",
            "narrative_hint": "Граница пастбища, часто с остатками ограждений.",
        },
        "bee_patch": {
            "spawn_weight": 15,
            "travel_cost": 1.1,
            "is_passable": True,
            "visual_tags": ["flower_clusters", "quiet_buzz", "sunlit_spots"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Участок, богатый цветами и насекомыми.",
        },
        "meadow_path": {
            "spawn_weight": 0,
            "travel_cost": 0.8,
            "is_passable": True,
            "visual_tags": ["trampled_line", "lower_grass", "animal_tracks"],
            "danger_mod": 0.7,
            "role": "background",
            "narrative_hint": "Пешеходная тропа через луг.",
        },
        "echo_stone_circle": {
            "spawn_weight": 5,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["standing_stones", "moss_rings", "ritual_marks"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Каменный круг — возможный остаток места силы.",
        },
        "echo_abandoned_cart": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["broken_cart", "tattered_canvas", "scattered_goods"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Останки каравана, покинутого в спешке.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 0.9,
            "is_passable": True,
            "visual_tags": ["stone_frame", "flower_overgrowth", "quiet_runes"],
            "danger_mod": 1.2,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Врата, засыпанные травой, но ещё сохраняющие форму.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["thin_rift", "cold_whisper", "sparking_motes"],
            "danger_mod": 1.5,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Тонкий разрыв, время от времени расползающийся.",
        },
    },
    # --- 5. HILLS (Холмы) ---
    "hills": {
        "soft_ridge": {
            "spawn_weight": 30,
            "travel_cost": 1.4,
            "is_passable": True,
            "visual_tags": ["gentle_slope", "thin_trees", "rock_patches"],
            "danger_mod": 1.1,
            "role": "background",
            "narrative_hint": "Пологие гряды холмов, дающие обзор.",
        },
        "steep_hill": {
            "spawn_weight": 20,
            "travel_cost": 1.8,
            "is_passable": True,
            "visual_tags": ["sharp_ascent", "loose_stones", "wide_view"],
            "danger_mod": 1.3,
            "role": "background",
            "narrative_hint": "Крутые подъёмы, местами опасные из-за обвала.",
        },
        "wind_crown": {
            "spawn_weight": 15,
            "travel_cost": 1.5,
            "is_passable": True,
            "visual_tags": ["high_top", "constant_wind", "short_plants"],
            "danger_mod": 1.2,
            "role": "background",
            "narrative_hint": "Возвышенность, где ветер никогда не утихает.",
        },
        "low_pass": {
            "spawn_weight": 20,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["narrow_valley", "cool_air", "shadow_sides"],
            "danger_mod": 1.1,
            "role": "background",
            "narrative_hint": "Узкий проход между холмами.",
        },
        "thorn_side": {
            "spawn_weight": 15,
            "travel_cost": 1.6,
            "is_passable": True,
            "visual_tags": ["dry_bushes", "hard_branches", "uneven_ground"],
            "danger_mod": 1.4,
            "role": "background",
            "narrative_hint": "Полоса колючих кустов, усложняющая проход.",
        },
        "hill_path": {
            "spawn_weight": 0,
            "travel_cost": 1.1,
            "is_passable": True,
            "visual_tags": ["zigzag_trail", "crumbled_rocks", "dusty_turns"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Тропа, петляющая по склонам.",
        },
        "echo_watch_pillar": {
            "spawn_weight": 5,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["stone_pillar", "weathered_marks", "high_view"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Башенка-наблюдатель — остаток сторожевой системы.",
        },
        "echo_herd_tracks": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["wide_tracks", "flattened_grass", "hoof_marks"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Следы массового передвижения — натянутые судьбы прошлого.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 1.3,
            "is_passable": True,
            "visual_tags": ["stone_gateway", "wind_scored", "etched_circle"],
            "danger_mod": 1.4,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Врата на вершине холма, видимые издалека.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 1.5,
            "is_passable": True,
            "visual_tags": ["ground_crack", "updrafts", "violet_smear"],
            "danger_mod": 1.7,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Разлом, втягивающий воздух и издающий низкий гул.",
        },
    },
    # --- 6. MOUNTAINS (Горы) ---
    "mountains": {
        "cliff_route": {
            "spawn_weight": 20,
            "travel_cost": 0.0,
            "is_passable": False,
            "visual_tags": ["high_drop", "rough_rock", "echo_wind"],
            "danger_mod": 0.0,
            "role": "background",
            "narrative_hint": "Непроходимые обрывы — природные барьеры.",
        },
        "ridge_line": {
            "spawn_weight": 20,
            "travel_cost": 2.2,
            "is_passable": True,
            "visual_tags": ["narrow_spine", "cold_air", "scattered_stones"],
            "danger_mod": 1.6,
            "role": "background",
            "narrative_hint": "Тонкая гряда камней с резким перепадом высот.",
        },
        "boulder_run": {
            "spawn_weight": 20,
            "travel_cost": 2.0,
            "is_passable": True,
            "visual_tags": ["huge_rocks", "unstable_ground", "dark_gaps"],
            "danger_mod": 1.5,
            "role": "background",
            "narrative_hint": "Поля крупных валунов — опасность оползней.",
        },
        "plateau": {
            "spawn_weight": 20,
            "travel_cost": 1.8,
            "is_passable": True,
            "visual_tags": ["flat_height", "strong_wind", "distant_view"],
            "danger_mod": 1.4,
            "role": "background",
            "narrative_hint": "Плоская вершина, часто используемая как стоянка.",
        },
        "mount_lake_edge": {
            "spawn_weight": 20,
            "travel_cost": 1.5,
            "is_passable": True,
            "visual_tags": ["clear_water", "cold_shore", "stone_rings"],
            "danger_mod": 1.2,
            "role": "background",
            "narrative_hint": "Берег горного озера — редкая пресная вода.",
        },
        "zigzag_path": {
            "spawn_weight": 0,
            "travel_cost": 1.4,
            "is_passable": True,
            "visual_tags": ["sharp_turns", "steep_slope", "dust_puffs"],
            "danger_mod": 1.1,
            "role": "background",
            "narrative_hint": "Серповидный путь, прокладывающий подъём.",
        },
        "echo_summit_remains": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["cracked_plinth", "ancient_inscription", "cold_wind"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Фрагменты святилища на высоте — знак древней попытки поклонения.",
        },
        "echo_abandoned_cable": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["rusted_cable", "broken_pole", "torn_gear"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Остатки транспортной системы, оборванной катастрофой.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 2.0,
            "is_passable": True,
            "visual_tags": ["stone_arch_high", "wind_etched", "frozen_runes"],
            "danger_mod": 1.9,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Высокие каменные врата — вход в древние маршруты.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 2.2,
            "is_passable": True,
            "visual_tags": ["gravity_breach", "levitating_stones", "thin_void"],
            "danger_mod": 2.0,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Разлом, искривляющий гравитацию и пространство.",
        },
    },
    # --- 7. CANYON (Каньон) ---
    "canyon": {
        "red_wall": {
            "spawn_weight": 25,
            "travel_cost": 0.0,
            "is_passable": False,
            "visual_tags": ["tall_cliffs", "warm_stone", "narrow_light"],
            "danger_mod": 0.0,
            "role": "background",
            "narrative_hint": "Отвесные стены каньона — ограничивают перемещение.",
        },
        "slot_pass": {
            "spawn_weight": 20,
            "travel_cost": 1.8,
            "is_passable": True,
            "visual_tags": ["tight_twist", "echo_steps", "cool_shade"],
            "danger_mod": 1.5,
            "role": "background",
            "narrative_hint": "Узкий проход между скал — место засад.",
        },
        "dry_bottom": {
            "spawn_weight": 25,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["cracked_ground", "stone_chunks", "thin_stream"],
            "danger_mod": 1.3,
            "role": "background",
            "narrative_hint": "Дно каньона — ровная, но опасная зона.",
        },
        "overhang": {
            "spawn_weight": 15,
            "travel_cost": 1.5,
            "is_passable": True,
            "visual_tags": ["shadow_ledge", "smooth_rock", "drip_marks"],
            "danger_mod": 1.4,
            "role": "background",
            "narrative_hint": "Выдающиеся выступы и свешивающиеся скалы.",
        },
        "old_steps": {
            "spawn_weight": 15,
            "travel_cost": 1.6,
            "is_passable": True,
            "visual_tags": ["carved_stairs", "sand_pockets", "broken_edges"],
            "danger_mod": 1.2,
            "role": "background",
            "narrative_hint": "Каменные ступени — следы древних переходов.",
        },
        "canyon_cross": {
            "spawn_weight": 0,
            "travel_cost": 1.1,
            "is_passable": True,
            "visual_tags": ["wide_opening", "mixed_stone", "bright_sky"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Перекрёсток каньона — просторное место пересечения путей.",
        },
        "echo_carved_relief": {
            "spawn_weight": 5,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["cliff_relief", "ancient_carving", "sand_rim"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Барельеф в скале — след рук старой культуры.",
        },
        "echo_dry_relic": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["parched_relic", "salt_crust", "etched_metal"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Коррозированный артефакт — свидетель технологической эры.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 1.1,
            "is_passable": True,
            "visual_tags": ["stone_span", "cliff_gate", "etched_ring"],
            "danger_mod": 1.6,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Врата, встроенные в стену каньона.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 1.3,
            "is_passable": True,
            "visual_tags": ["chasm_breach", "cold_wisp", "thin_light"],
            "danger_mod": 1.8,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Разлом в трещине каньона — источник аномалий.",
        },
    },
    # --- 8. GRASSLAND (Степь) ---
    "grassland": {
        "steppe_plain": {
            "spawn_weight": 30,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["wide_field", "dry_grass", "constant_wind"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Открытая степь — широкие горизонты и ветер.",
        },
        "dry_basin": {
            "spawn_weight": 20,
            "travel_cost": 1.1,
            "is_passable": True,
            "visual_tags": ["shallow_dip", "hard_soil", "grainy_dust"],
            "danger_mod": 1.1,
            "role": "background",
            "narrative_hint": "Сухая впадина, собирающая пыль и следы.",
        },
        "gullies": {
            "spawn_weight": 15,
            "travel_cost": 1.4,
            "is_passable": True,
            "visual_tags": ["small_ravines", "soft_slopes", "hidden_shadows"],
            "danger_mod": 1.3,
            "role": "background",
            "narrative_hint": "Небольшие овражки и укрытия.",
        },
        "shear_steppe": {
            "spawn_weight": 20,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["tough_grass", "low_sage", "dust_spots"],
            "danger_mod": 1.2,
            "role": "background",
            "narrative_hint": "Участок с жесткой растительностью и малой видимостью.",
        },
        "nomad_trace": {
            "spawn_weight": 15,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["long_track", "trampled_soil", "wide_view"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Следы передвижения кочевников.",
        },
        "old_path": {
            "spawn_weight": 0,
            "travel_cost": 0.8,
            "is_passable": True,
            "visual_tags": ["worn_line", "thin_tracks", "edge_grass"],
            "danger_mod": 0.8,
            "role": "background",
            "narrative_hint": "Старая дорожная линия, пересекающая степь.",
        },
        "echo_crumbled_silo": {
            "spawn_weight": 5,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["collapsed_silo", "grain_spatter", "rusted_hull"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Развалившийся силос — след хозяйственной жизни.",
        },
        "echo_nomad_cairn": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["stone_cairn", "travel_marks", "wind_smoothed"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Каменные знаки путников — ориентиры прошлого.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["open_arch", "dust_ring", "etched_panel"],
            "danger_mod": 1.4,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Врата, стоящие посреди равнины как памятник утрате.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["soil_rend", "scent_of_void", "faint_light"],
            "danger_mod": 1.7,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Разлом, остающийся после вспышек энергии.",
        },
    },
    # --- 9. SAVANNA (Саванна) ---
    "savanna": {
        "thorn_plain": {
            "spawn_weight": 25,
            "travel_cost": 1.3,
            "is_passable": True,
            "visual_tags": ["dry_bushes", "tall_grass", "open_sun"],
            "danger_mod": 1.3,
            "role": "background",
            "narrative_hint": "Пестрая саванна с редкими деревьями.",
        },
        "acacia_spread": {
            "spawn_weight": 25,
            "travel_cost": 1.1,
            "is_passable": True,
            "visual_tags": ["wide_acacias", "light_shade", "warm_soil"],
            "danger_mod": 1.1,
            "role": "background",
            "narrative_hint": "Группы акаций, дарующие тень и укрытие.",
        },
        "dust_run": {
            "spawn_weight": 20,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["red_sand", "fast_wind", "bare_patches"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Пыльные полосы, легко выдающие следы.",
        },
        "termite_zone": {
            "spawn_weight": 15,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["tall_mounds", "dry_earth", "scattered_stones"],
            "danger_mod": 1.2,
            "role": "background",
            "narrative_hint": "Многочисленные термитники и почвенные структуры.",
        },
        "water_hollow": {
            "spawn_weight": 15,
            "travel_cost": 1.4,
            "is_passable": True,
            "visual_tags": ["small_pool", "soft_mud", "animal_tracks"],
            "danger_mod": 1.4,
            "role": "background",
            "narrative_hint": "Небольшие водоёмы — жизненно важные точки для фауны.",
        },
        "savanna_trail": {
            "spawn_weight": 0,
            "travel_cost": 0.9,
            "is_passable": True,
            "visual_tags": ["wide_track", "broken_grass", "sun_glare"],
            "danger_mod": 0.9,
            "role": "background",
            "narrative_hint": "Широкий путь, часто используемый миграциями.",
        },
        "echo_hollow_tree": {
            "spawn_weight": 5,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["hollow_trunk", "scratch_marks", "small_cache"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Древо с полостью — укрытие или хранилище прошлых путников.",
        },
        "echo_ash_swale": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["ash_patch", "charred_stone", "heat_warp"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Пятно выжженной земли — след близкой катастрофы.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["sun_bronzed_arch", "dried_runes", "sand_ring"],
            "danger_mod": 1.5,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Врата, окрашенные солнцем и пылью.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["heat_rend", "swirling_spores", "thin_void"],
            "danger_mod": 1.8,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Пробой реальности, приносящий странные шорохи.",
        },
    },
    # --- 10. JUNGLE (Джунгли) ---
    "jungle": {
        "dense_green": {
            "spawn_weight": 30,
            "travel_cost": 2.5,
            "is_passable": True,
            "visual_tags": ["thick_canopy", "dark_underwood", "wet_air"],
            "danger_mod": 1.8,
            "role": "background",
            "narrative_hint": "Густой подлесок, где свет пробивается едва.",
        },
        "root_tangle": {
            "spawn_weight": 20,
            "travel_cost": 2.2,
            "is_passable": True,
            "visual_tags": ["high_roots", "soft_mud", "dim_light"],
            "danger_mod": 1.6,
            "role": "background",
            "narrative_hint": "Корни плетут лабиринты на поверхности земли.",
        },
        "vine_wall": {
            "spawn_weight": 20,
            "travel_cost": 2.8,
            "is_passable": True,
            "visual_tags": ["curtain_vines", "heavy_shade", "humid_breath"],
            "danger_mod": 1.7,
            "role": "background",
            "narrative_hint": "Стены из лоз, скрывающие проходы и ловушки.",
        },
        "jungle_edge": {
            "spawn_weight": 15,
            "travel_cost": 1.5,
            "is_passable": True,
            "visual_tags": ["thinner_trees", "bright_spots", "soft_ground"],
            "danger_mod": 1.2,
            "role": "background",
            "narrative_hint": "Край джунглей, где природа разрежена.",
        },
        "fallen_giant": {
            "spawn_weight": 15,
            "travel_cost": 2.0,
            "is_passable": True,
            "visual_tags": ["massive_trunk", "moss_patch", "insect_swarm"],
            "danger_mod": 1.5,
            "role": "background",
            "narrative_hint": "Поваленное дерево-гигант — препятствие и дом.",
        },
        "jungle_path": {
            "spawn_weight": 0,
            "travel_cost": 1.3,
            "is_passable": True,
            "visual_tags": ["narrow_line", "broken_branches", "leaf_pile"],
            "danger_mod": 1.1,
            "role": "background",
            "narrative_hint": "Узкий тропический путь.",
        },
        "echo_subterranean_ruin": {
            "spawn_weight": 5,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["stone_steps", "overgrown_carvings", "humid_air"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Погребённый храм — старые залы, теперь заваленные корнями.",
        },
        "echo_broken_ceramics": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["shattered_pottery", "mossy_fragments", "tiny_glyphs"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Осколки посуды и украшений — признаки повседневной жизни.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 1.8,
            "is_passable": True,
            "visual_tags": ["vine_wrapped_arch", "dripping_runes", "sapped_glow"],
            "danger_mod": 1.9,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Врата, опутанные растениями и испускающие легкий свет.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 2.0,
            "is_passable": True,
            "visual_tags": ["sundered_air", "humming_fog", "swirling_leaves"],
            "danger_mod": 2.1,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Разлом, искажая звук и движение вокруг.",
        },
    },
    # --- 11. MARSH (Заливные луга / топи) ---
    "marsh": {
        "wet_plain": {
            "spawn_weight": 30,
            "travel_cost": 1.8,
            "is_passable": True,
            "visual_tags": ["shallow_water", "soft_soil", "green_mist"],
            "danger_mod": 1.3,
            "role": "background",
            "narrative_hint": "Поля с водой, переходящие в болото.",
        },
        "reed_belt": {
            "spawn_weight": 20,
            "travel_cost": 2.2,
            "is_passable": True,
            "visual_tags": ["dense_reeds", "swaying_stalks", "water_trails"],
            "danger_mod": 1.4,
            "role": "background",
            "narrative_hint": "Пояс тростника, скрывающий мелкие ручьи.",
        },
        "miry_field": {
            "spawn_weight": 20,
            "travel_cost": 2.0,
            "is_passable": True,
            "visual_tags": ["soft_mire", "wet_grass", "slow_drip"],
            "danger_mod": 1.5,
            "role": "background",
            "narrative_hint": "Топкие поля с зыбкой почвой.",
        },
        "muddy_edge": {
            "spawn_weight": 15,
            "travel_cost": 1.6,
            "is_passable": True,
            "visual_tags": ["slick_ground", "thin_trees", "dark_water"],
            "danger_mod": 1.3,
            "role": "background",
            "narrative_hint": "Грязные прибрежные зоны с низкой проходимостью.",
        },
        "flood_channel": {
            "spawn_weight": 15,
            "travel_cost": 2.5,
            "is_passable": True,
            "visual_tags": ["narrow_stream", "wet_banks", "smooth_stones"],
            "danger_mod": 1.6,
            "role": "background",
            "narrative_hint": "Узкие протоки, по которым уходит вода.",
        },
        "marsh_path": {
            "spawn_weight": 0,
            "travel_cost": 1.4,
            "is_passable": True,
            "visual_tags": ["raised_planks", "rusted_nails", "wet_creak"],
            "danger_mod": 1.1,
            "role": "background",
            "narrative_hint": "Набережные настилы и дорожки через марши.",
        },
        "echo_sunken_pavilion": {
            "spawn_weight": 5,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["submerged_pillars", "barnacled_steps", "reed_falls"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Полузатопленная постройка — отголосок цивилизации.",
        },
        "echo_tide_altar": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["algae_carved", "stone_basin", "water_etchings"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Алтарь, который когда-то служил наблюдением приливов.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 1.6,
            "is_passable": True,
            "visual_tags": ["boarded_arch", "silted_circle", "reed_wrapping"],
            "danger_mod": 1.8,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Врата, окружённые и поглощённые водой.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 1.8,
            "is_passable": True,
            "visual_tags": ["water_rend", "air_bubbles", "faint_hum"],
            "danger_mod": 2.0,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Разлом, проявляющийся в водной глади.",
        },
    },
    # --- 12. BADLANDS (Скальные пустоши) ---
    "badlands": {
        "sharp_shards": {
            "spawn_weight": 25,
            "travel_cost": 1.6,
            "is_passable": True,
            "visual_tags": ["jagged_rocks", "thin_sand", "dry_air"],
            "danger_mod": 1.4,
            "role": "background",
            "narrative_hint": "Острые осколки скал и эрозионные формы.",
        },
        "painted_cliffs": {
            "spawn_weight": 20,
            "travel_cost": 0.0,
            "is_passable": False,
            "visual_tags": ["layered_stone", "color_stripes", "crumbled_edges"],
            "danger_mod": 0.0,
            "role": "background",
            "narrative_hint": "Крутые и яркие страты осадочных пород.",
        },
        "flat_table": {
            "spawn_weight": 20,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["high_plateau", "open_wind", "dry_rim"],
            "danger_mod": 1.2,
            "role": "background",
            "narrative_hint": "Высокие утёсы и плоские вершины.",
        },
        "cinder_field": {
            "spawn_weight": 20,
            "travel_cost": 1.5,
            "is_passable": True,
            "visual_tags": ["black_sand", "hot_spots", "rough_stone"],
            "danger_mod": 1.5,
            "role": "background",
            "narrative_hint": "Поле обугленной породы и горячих пятен.",
        },
        "broken_spires": {
            "spawn_weight": 15,
            "travel_cost": 1.8,
            "is_passable": True,
            "visual_tags": ["thin_towers", "falling_gravel", "red_dust"],
            "danger_mod": 1.3,
            "role": "background",
            "narrative_hint": "Разрушенные шпили — природные памятники эрозии.",
        },
        "badland_path": {
            "spawn_weight": 0,
            "travel_cost": 1.1,
            "is_passable": True,
            "visual_tags": ["zigzag_line", "scorched_ground", "loose_stones"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Тропа через пустоши и расщелины.",
        },
        "echo_pillar_ruins": {
            "spawn_weight": 5,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["crumbled_pillars", "sand_shelves", "etched_band"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Остатки колонн — руины древних построек.",
        },
        "echo_iron_scaffold": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["rusted_scaffold", "weathered_beam", "bolt_holes"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Промышленные остатки, покрытые пылью.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 1.3,
            "is_passable": True,
            "visual_tags": ["eroded_arch", "dusted_runes", "stone_podium"],
            "danger_mod": 1.6,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Врата, высеченные в плотном камне.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 1.5,
            "is_passable": True,
            "visual_tags": ["shell_rend", "silica_drift", "low_hum"],
            "danger_mod": 1.9,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Место, где земля раскалывается на тонкие слябы.",
        },
    },
    # --- 13. HIGHLANDS (Нагорья) ---
    "highlands": {
        "wind_plate": {
            "spawn_weight": 30,
            "travel_cost": 1.3,
            "is_passable": True,
            "visual_tags": ["open_top", "strong_gusts", "yellow_grass"],
            "danger_mod": 1.1,
            "role": "background",
            "narrative_hint": "Пузыри нагорий — обширные возвышения с сильным ветром.",
        },
        "mesa_edge": {
            "spawn_weight": 20,
            "travel_cost": 0.0,
            "is_passable": False,
            "visual_tags": ["sheer_drop", "flat_cliff", "dry_rocks"],
            "danger_mod": 0.0,
            "role": "background",
            "narrative_hint": "Крутые края месы, недоступные пешему прохождению.",
        },
        "stony_field": {
            "spawn_weight": 25,
            "travel_cost": 1.4,
            "is_passable": True,
            "visual_tags": ["wide_rocks", "thin_grass", "close_horizon"],
            "danger_mod": 1.2,
            "role": "background",
            "narrative_hint": "Каменные поля, усеянные плоскими валунами.",
        },
        "high_pass": {
            "spawn_weight": 15,
            "travel_cost": 1.6,
            "is_passable": True,
            "visual_tags": ["narrow_route", "cold_flow", "rough_walls"],
            "danger_mod": 1.4,
            "role": "background",
            "narrative_hint": "Проходы между высокими грядами.",
        },
        "shepherd_camp": {
            "spawn_weight": 10,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["old_stones", "light_smoke", "open_space"],
            "danger_mod": 0.9,
            "role": "background",
            "narrative_hint": "Малые стоянки и остатки полевых лагерей.",
        },
        "ridge_path": {
            "spawn_weight": 0,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["ridge_line", "fast_wind", "dust_cut"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Широкая тропа по гребням нагорий.",
        },
        "echo_watch_circle": {
            "spawn_weight": 5,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["stone_ring", "weathered_marks", "thin_grass"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Каменный круг — место наблюдения и сигнала.",
        },
        "echo_old_shepherd_shack": {
            "spawn_weight": 4,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["lean_shack", "smoke_stain", "torn_cloth"],
            "danger_mod": 0.0,
            "role": "echo",
            "narrative_hint": "Остатки простого жилища — следы человеческого присутствия.",
        },
        "ancient_gateway_inactive": {
            "spawn_weight": 1,
            "travel_cost": 1.3,
            "is_passable": True,
            "visual_tags": ["mesa_gateway", "etched_plinth", "wind_veil"],
            "danger_mod": 1.5,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Врата на плато — ориентир для путников.",
        },
        "rift_spawn_point": {
            "spawn_weight": 1,
            "travel_cost": 1.5,
            "is_passable": True,
            "visual_tags": ["plateau_tear", "air_billow", "distant_hum"],
            "danger_mod": 1.8,
            "role": "landmark",
            "is_unique": True,
            "narrative_hint": "Разлом, вырывающийся на плоской поверхности.",
        },
    },
    # --- 14. CITY RUINS (Руины Города - весь регион D4) ---
    "city_ruins": {
        # --- ФОН (Улицы и фундаменты) ---
        "ancient_pavement": {
            "spawn_weight": 40,
            "travel_cost": 0.9,  # По городу ходить легко
            "is_passable": True,
            "visual_tags": ["cobblestone", "cracked_stone", "city_street"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Старая мощеная улица, местами вздыбленная корнями.",
        },
        "ruined_foundation": {
            "spawn_weight": 30,
            "travel_cost": 1.2,
            "is_passable": True,
            "visual_tags": ["stone_base", "rotten_beams", "debris_pile"],
            "danger_mod": 1.1,
            "role": "background",
            "narrative_hint": "Фундамент разрушенного дома, заваленный мусором. Хорошее место для сбора ресурсов.",
        },
        # --- СТЕНЫ (Барьеры) ---
        "monolithic_wall": {
            "spawn_weight": 0,  # Спавнится только скриптом по краям
            "travel_cost": 0.0,
            "is_passable": False,
            "visual_tags": ["obsidian_wall", "glowing_runes", "unscalable"],
            "danger_mod": 0.0,
            "role": "background",
            "narrative_hint": "Массивная внешняя стена из черного камня, защищающая город.",
        },
        "inner_wall_section": {
            "spawn_weight": 0,
            "travel_cost": 0.0,
            "is_passable": False,
            "visual_tags": ["old_brick_wall", "defense_line", "broken_parapet"],
            "danger_mod": 0.0,
            "role": "background",
            "narrative_hint": "Внутренняя стена, отделяющая цитадель от жилых кварталов.",
        },
        # --- LANDMARKS (Точки интереса в городе) ---
        "city_gate_outer": {
            "spawn_weight": 0,
            "travel_cost": 0.2,
            "is_passable": True,
            "visual_tags": ["massive_gate", "portcullis", "guard_room"],
            "danger_mod": 1.5,
            "role": "landmark",
            "is_unique": True,
            "service_key": "gate_mechanism",  # Можно закрывать/открывать
            "narrative_hint": "Главные ворота внешней стены.",
        },
        "ruined_library": {
            "spawn_weight": 1,
            "travel_cost": 1.0,
            "is_passable": True,
            "visual_tags": ["tattered_books", "scroll_shelves", "stone_dome"],
            "danger_mod": 1.2,
            "role": "echo",  # Лорный объект
            "narrative_hint": "Остатки архива или библиотеки.",
        },
        # Добавь это в секцию "city_ruins"
        "ruin_road_main": {
            "spawn_weight": 0,  # Только процедурно (через PathFinder)
            "travel_cost": 0.8,  # Быстрее, чем по завалам
            "is_passable": True,
            "visual_tags": ["cleared_path", "cracked_pavement", "piles_on_sides"],
            "danger_mod": 1.0,
            "role": "background",
            "narrative_hint": "Расчищенная полоса дороги, идущая сквозь руины квартала.",
        },
    },
}


# ==============================================================================
# 3. ЯКОРЯ СТИХИЙ (ANCHORS)
# Источник Глобальных тегов (влияют на весь Регион).
# ==============================================================================
class AnchorData(TypedDict):
    x: int
    y: int
    power: float
    falloff: float
    type: str
    narrative_tags: list[str]


ANCHORS: list[AnchorData] = [
    # --- СЕВЕР (A1): Лед, Стазис (Левый Верхний Угол) ---
    {
        "x": 7,
        "y": 7,
        "power": 1.2,
        "falloff": 0.08,
        "type": "north_prime",
        "narrative_tags": ["frozen", "ice_crystals", "ancient_tech", "stasis"],
    },
    # --- ЮГ (G7): Огонь, Пепел (Правый Нижний Угол) ---
    {
        "x": 97,
        "y": 97,
        "power": 1.2,
        "falloff": 0.08,
        "type": "south_prime",
        "narrative_tags": ["magma", "ash", "scorched_earth", "smoke"],
    },
    # --- ЗАПАД (G1): Гравитация, Шторм (Левый Нижний Угол) ---
    {
        "x": 7,
        "y": 97,
        "power": 1.2,
        "falloff": 0.08,
        "type": "west_prime",
        "narrative_tags": ["zero_gravity", "floating_rocks", "storm", "lightning"],
    },
    # --- ВОСТОК (A7): Биомасса, Яд (Правый Верхний Угол) ---
    {
        "x": 97,
        "y": 7,
        "power": 1.2,
        "falloff": 0.08,
        "type": "east_prime",
        "narrative_tags": ["biomass", "giant_roots", "poison_spores", "mutation"],
    },
]

# ==============================================================================
# ПАРАМЕТРЫ ПОРТАЛА (ЗАЩИТНОЕ ПОЛЕ)
# ==============================================================================
# Power 2.5 перебивает влияние Анкоров (1.2) в радиусе D4.
# Falloff 0.03 делает границу мягкой.
PORTAL_PARAMS = {"power": 2.5, "falloff": 0.03}


# ==============================================================================
# 4. ГРАДИЕНТЫ ТЕГОВ (THE GRADIENTS)
# Вместо статических палитр мы используем динамические наборы тегов,
# зависящие от Уровня Угрозы (Tier) в конкретной точке.
# Tier рассчитывается в ThreatService (0..7).
# ==============================================================================
# ==============================================================================
# 4. ГРАДИЕНТЫ ТЕГОВ (THE GRADIENTS)
# ==============================================================================
INFLUENCE_TAGS = {
    # --- СЕВЕР (ЛЕД) ---
    "ice": {
        # Tier 0: ВНУТРИ ХАБА (Эхо энергии)
        # Не "мороз", а "дыхание стазиса".
        (0, 0): ["unnatural_chill", "hoarfrost_on_runes", "breath_vapor", "still_air"],
        # Tier 1-2: ОКРАИНА ГОРОДА / СТЕНЫ
        (1, 2): ["frozen_dew", "cold_stone", "thin_ice_crust", "numbing_breeze"],
        # Tier 3-4: ПУСТОШЬ (Влияние)
        (3, 4): ["deep_snow", "frozen_puddles", "ice_shards", "biting_wind"],
        # Tier 5-7: ЭПИЦЕНТР (Смерть)
        (5, 7): ["absolute_zero", "time_stasis", "floating_ice_monoliths", "crystal_prison"],
    },
    # --- ЮГ (ОГОНЬ) ---
    "fire": {
        # Tier 0: ВНУТРИ ХАБА
        (0, 0): ["warm_stone_floor", "smell_of_ozone", "dry_throat", "distant_hum"],
        # Tier 1-2: ОКРАИНА
        (1, 2): ["heat_haze", "warm_wind", "smell_of_sulfur", "hot_dust"],
        # Tier 3-4: ПУСТОШЬ
        (3, 4): ["smoking_ground", "scorched_grass", "burnt_soil", "falling_ash"],
        # Tier 5-7: ЭПИЦЕНТР
        (5, 7): ["magma_ocean", "fire_storms", "obsidian_spikes", "melting_reality"],
    },
    # --- ЗАПАД (ГРАВИТАЦИЯ) ---
    "gravity": {
        # Tier 0: ВНУТРИ ХАБА
        (0, 0): ["static_tingle", "dust_motes_hovering", "light_steps", "hair_raising"],
        # Tier 1-2: ОКРАИНА
        (1, 2): ["floating_pebbles", "distorted_horizon", "electric_hum", "pressure_drop"],
        # Tier 3-4: ПУСТОШЬ
        (3, 4): ["low_gravity", "constant_lightning", "magnetic_wind", "vertigo"],
        # Tier 5-7: ЭПИЦЕНТР
        (5, 7): ["void_rifts", "inverted_gravity", "shattered_sky", "storm_wall"],
    },
    # --- ВОСТОК (БИО) ---
    "bio": {
        # Tier 0: ВНУТРИ ХАБА
        (0, 0): ["sweet_sickness_scent", "vibrant_colors", "accelerated_growth", "spores_in_light"],
        # Tier 1-2: ОКРАИНА
        (1, 2): ["mossy_patches", "strange_flowers", "thick_air", "insect_hum"],
        # Tier 3-4: ПУСТОШЬ
        (3, 4): ["giant_roots", "glowing_fungi", "thick_pollen", "rapid_mutation"],
        # Tier 5-7: ЭПИЦЕНТР
        (5, 7): ["flesh_landscape", "giant_beating_hearts", "hive_mind", "mutation_source"],
    },
}

# ==============================================================================
# 5. ЗОНЫ СМЕШИВАНИЯ (DIAGONAL OVERLAPS)
# Теги, которые добавляются, если в точке сильно влияние ДВУХ стихий.
# (Рассчитывается в ThreatService: если power_1 > X и power_2 > X)
# ==============================================================================
HYBRID_TAGS = {
    # Север (Лед) + Запад (Гравитация) = Ледяной Шторм
    frozenset(["ice", "gravity"]): ["hail_storm", "frozen_lightning", "shattering_sky"],
    # Север (Ле-д) + Восток (Био) = Крио-Сон / Сохранение
    frozenset(["ice", "bio"]): ["preserved_corpses", "frozen_flowers", "hibernate"],
    # Юг (Огонь) + Запад (Гравитация) = Плазменный Шторм
    frozenset(["fire", "gravity"]): ["plasma_arcs", "flying_lava", "solar_flare"],
    # Юг (Огонь) + Восток (Био) = Гниение / Болото (Тепло + Влага)
    frozenset(["fire", "bio"]): ["boiling_swamp", "rotting_flesh", "steam", "disease"],
}


# ==============================================================================
# 6. ВИЗУАЛЬНЫЕ ДОМИНАНТЫ (LANDMARKS)
# Используются ZoneOrchestrator для создания контекстных подсказок.
# ==============================================================================
VISUAL_DOMINANTS: dict[str, list[str]] = {
    "structures": ["gate", "bastion", "tower", "ruins_skyscraper", "portal", "wall"],
    "nature": ["mountain_peak", "giant_tree", "volcano", "floating_island"],
    "threats": ["magma_ocean", "void_rift", "hive_mind"],
    "echo": ["ruins", "fallen_statue", "ancient_machine", "broken_road", "stone_circle"],
    "landmarks": ["ancient_gateway_inactive", "rift_spawn_point", "fortress_ruin", "old_tower", "monolith_core"],
}

# ==============================================================================
# 7. ДОРОЖНЫЕ ТЕГИ
# Используются для стыковки дорог между чанками.
# ==============================================================================
ROAD_TAGS: list[str] = ["road", "path", "highway", "bridge", "track", "broken_road"]
