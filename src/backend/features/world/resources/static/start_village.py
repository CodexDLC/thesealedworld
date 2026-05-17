from typing import Any, NotRequired, TypedDict


class _StaticLocationContent(TypedDict):
    title: str
    description: str
    background_url: NotRequired[str]
    environment_tags: list[str]


class _StaticLocation(TypedDict):
    sector_id: str
    is_active: bool
    services: list[str]
    flags: dict[str, Any]
    movement_profile: dict[str, Any]
    visual_overrides: NotRequired[dict[str, Any]]
    content: _StaticLocationContent


# ==============================================================================
# СТАТИЧНЫЕ ЛОКАЦИИ: КРУГ ИСХОДА, СТАБИЛЬНЫЙ ЦЕНТР АУР-ЭНТАРА (5x5)
# Сеттинг: древняя техномагическая столица Аур-Энтар вокруг портальной площади Исхода.
# Временные постройки выживших вторичны и не должны вытеснять монолитную архитектуру.
# ==============================================================================
STATIC_LOCATIONS: dict[tuple[int, int], _StaticLocation] = {
    # ---------------------------------------------------------
    # ЦЕНТР: РУННЫЙ КРУГ
    # ---------------------------------------------------------
    (52, 52): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_portal_hub"],
        "flags": {"is_active": True, "is_safe_zone": True, "is_hub": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "visual_overrides": {
            "image_profile": "d4_capital_hub",
            "node_role": "portal_plaza",
            "composition": (
                "the preserved portal plaza is the landmark; the central circular platform stays almost perfect, "
                "broken ceremonial arches frame the distance, survivor tents remain small at the outer rim"
            ),
            "forbidden": ["sci-fi terminal", "hologram", "readable runes", "crowd of people"],
        },
        "content": {
            "title": "Площадь Исхода",
            "description": "Центральная платформа Аур-Энтара лежит под открытым небом: огромный круг из белого и черного монолита, где радиальные каналы сходятся к мертвому портальному ядру. Планетарный ИИ удерживает здесь ровное, почти стерильное пространство, а бедные палатки и костры жмутся только к дальним краям площади.",
            "background_url": "/static/images/exploration/city/d4/52_52_runic_circle_plaza.png",
            "environment_tags": [
                "hub_center",
                "active_portal",
                "runic_circle",
                "ancient_city",
                "safe_zone",
                "street",
                "tents",
            ],
        },
    },
    # ---------------------------------------------------------
    # ВНУТРЕННИЕ КВАРТАЛЫ (СЕРВИСЫ И ЖИЛЬЕ)
    # ---------------------------------------------------------
    # --- Северный сектор ---
    (52, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_arena_main"],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Северный Проспект Башни",
            "description": "Северный проспект тянется от Площади Исхода к глухой башне без окон, выточенной из цельного черного монолита. Сама улица остается частью эвакуационного маршрута, а арена внутри башни — уже позднее использование сохранившегося тренировочного объема.",
            "background_url": "/static/images/exploration/city/d4/52_51_trial_tower_street.png",
            "environment_tags": ["ancient_tower", "magic_pocket", "ruins", "street", "arena"],
        },
    },
    (51, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Квартал Теней",
            "description": "Здесь улицы сжаты между высокими фасадами черного монолита, и свет словно вязнет в гладких стенах. Старые сервисные ниши закрыты мертвыми створками, но иногда в глубине вспыхивает тонкая золотая жила, напоминая, что Круг Исхода все еще поддерживается.",
            "background_url": "/static/images/exploration/city/d4/51_51_shadow_quarter.png",
            "environment_tags": ["ruins", "debris", "resource_spot", "street", "dark_alley", "monolith"],
        },
    },
    (53, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Руины Библиотеки",
            "description": "Библиотечный блок Аур-Энтара обрушился не как обычное здание: плиты архива лежат ровными слоями, будто их отключили посреди эвакуации. Между колоннами видны осторожные раскопы, но главная тяжесть места — молчащие хранилища знаний, которые пережили десятки тысяч лет.",
            "background_url": "/static/images/exploration/city/d4/53_51_library_ruins.png",
            "environment_tags": ["ruins", "debris", "resource_spot", "street", "ancient_knowledge"],
        },
    },
    # --- Южный сектор ---
    (52, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_tavern_hub"],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "visual_overrides": {
            "image_profile": "d4_capital_hub",
            "node_role": "tavern_refuge",
            "composition": (
                "the southern reception pavilion and its monolith street approach are the main scene; the warm refuge "
                "tavern occupies only one lower hall edge as a secondary human layer"
            ),
            "forbidden": ["busy crowd", "ordinary inn cottage", "medieval castle courtyard"],
        },
        "content": {
            "title": "Южный Приемный Павильон",
            "description": "Южнее площади раскрывается приемный павильон Аур-Энтара: широкий монолитный зал, боковые арки и потускневшие эфирные жилы в ребрах потолка. В одном нижнем пролете устроен 'Последний Приют', но таверна выглядит временным теплым углом внутри гораздо более древнего места.",
            "background_url": "/static/images/exploration/city/d4/52_53_last_refuge_tavern.png",
            "environment_tags": ["tavern", "ruins", "street", "safe_zone", "lively", "wood_patch"],
        },
    },
    (51, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Заваленный Квартал",
            "description": "Складской квартал перекрыт осевшими плитами, разорванными контейнерными нишами и мусором первых лет заселения. Под завалами угадываются входы в древние распределительные камеры, но ИИ держит проходы закрытыми, пока сектор не станет достаточно устойчивым.",
            "background_url": "/static/images/exploration/city/d4/51_53_blocked_quarter.png",
            "environment_tags": ["ruins", "debris", "resource_spot", "street", "barrels"],
        },
    },
    (53, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Квартал Ремесленников",
            "description": "В этих мастерских техномагия Аур-Энтара похожа на ремесло богов: цельные верстаки, холодные горны и каналы энергии встроены прямо в камень. Новые мастера используют лишь края этого наследия, чиня простые вещи там, где когда-то собирали механизмы эвакуации.",
            "background_url": "/static/images/exploration/city/d4/53_53_artisan_quarter.png",
            "environment_tags": ["ruins", "debris", "resource_spot", "street", "workshop"],
        },
    },
    # --- Западный сектор ---
    (51, 52): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_town_hall_hub", "svc_blacksmith_repair"],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Проспект Старейшин",
            "description": "Западный проспект сложен из плит без швов и держит строгую ось между административным залом и старой оружейной-мастерской. Совет и кузнечная служба занимают уцелевшие помещения по сторонам улицы, но главным здесь остается гражданское ядро древней столицы.",
            "background_url": "/static/images/exploration/city/d4/51_52_elders_avenue.png",
            "environment_tags": ["town_hall", "blacksmith", "ruins", "street", "paved_road"],
        },
    },
    # --- Восточный сектор ---
    (53, 52): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_market_hub"],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "visual_overrides": {
            "image_profile": "d4_capital_hub",
            "node_role": "market_square",
            "composition": (
                "the old eastern supply plaza is the main landmark, with monolith plinths and floor channels; poor barter "
                "tables and torn awnings sit on top as a secondary human layer without crowding the scene"
            ),
            "forbidden": ["people shopping", "readable shop signs", "normal medieval marketplace"],
        },
        "content": {
            "title": "Восточная Площадь Снабжения",
            "description": "Восточная площадь когда-то была узлом снабжения перед Исходом: низкие монолитные постаменты и сухие каналы в полу до сих пор задают ее порядок. Рынок новых жителей занимает только верхний слой этого места — товары, тенты и обменные столы разложены поверх древней схемы.",
            "background_url": "/static/images/exploration/city/d4/53_52_market_square.png",
            "environment_tags": ["market", "barter", "ruins", "street", "crowd", "tents"],
        },
    },
    # ---------------------------------------------------------
    # ПЕРИМЕТР: РУИНЫ У СТЕНЫ (50-54)
    # ---------------------------------------------------------
    # --- Северная стена ---
    (52, 50): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "is_gate": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "visual_overrides": {
            "image_profile": "d4_capital_hub",
            "node_role": "inner_gate",
            "composition": (
                "a massive northern inner ceremonial gate is the landmark; primitive wood reinforcement is visible "
                "but small against the ancient monolith arch and dead mechanisms"
            ),
            "forbidden": ["castle portcullis as main style", "guards", "letter D4"],
        },
        "content": {
            "title": "Северные Внутренние Ворота",
            "description": "Северная арка — часть внутреннего кольца консервации, а не крепостные ворота в обычном смысле. Родные створки исчезли во время Исхода, и грубая деревянная преграда лишь обозначает проход там, где мертвые механизмы стены все еще ждут команды.",
            "background_url": "/static/images/exploration/city/d4/52_50_north_inner_gate.png",
            "environment_tags": ["gate", "defense", "inner_wall", "ancient_city", "street", "wood_gate"],
        },
    },
    (51, 50): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["north"]},
        "content": {
            "title": "Руины Казарм",
            "description": "Длинный блок у северной стены похож на казармы только для нынешних глаз; раньше это был отсек размещения эвакуационных команд. Крыша разрушена, но монолитные перегородки целы, и пространство можно расчистить под склад, жилье или будущую службу охраны.",
            "background_url": "/static/images/exploration/city/d4/51_50_barracks_plot.png",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "barracks", "street"],
        },
    },
    (53, 50): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["north"]},
        "content": {
            "title": "Пустые Загоны",
            "description": "Ряд каменных ячеек у стены напоминает стойла, хотя их гладкая геометрия явно создана не для обычных животных. Сейчас здесь пусто и сухо; северная стена гасит ветер, а древние крепления в полу ждут нового назначения.",
            "background_url": "/static/images/exploration/city/d4/53_50_empty_stables.png",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "stable", "street"],
        },
    },
    # --- Южная стена ---
    (52, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "is_gate": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Южные Внутренние Ворота",
            "description": "Южный проход ведет к менее стабильным кварталам столицы, где защита ИИ уже не так ровна. Арка свободна, но вдоль ее ребер видны погасшие узлы отсечения: когда-то они могли закрыть сектор без створок и засовов.",
            "background_url": "/static/images/exploration/city/d4/52_54_south_inner_gate.png",
            "environment_tags": ["gate", "defense", "inner_wall", "ruins", "street"],
        },
    },
    (51, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["south"]},
        "content": {
            "title": "Руины Склада",
            "description": "У южной стены сохранился фундамент распределительного склада, заваленный крупными обломками белого монолита. Стена здесь особенно толстая и без трещин, поэтому участок ценят как редкое место, где можно строить, не опасаясь ночного сдвига руин.",
            "background_url": "/static/images/exploration/city/d4/51_54_warehouse_plot.png",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "warehouse", "street"],
        },
    },
    (53, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["south"]},
        "content": {
            "title": "Древний Горн",
            "description": "Высокий горн у южной стены не похож на кузницу: его дымоход сливается с каналами стены, а чаша печи вырезана из цельного черного камня. Пламя давно погасло, но если разбудить контуры, здесь снова можно будет вести производство.",
            "background_url": "/static/images/exploration/city/d4/53_54_ancient_forge.png",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "forge", "street"],
        },
    },
    # --- Западная стена ---
    (50, 52): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "is_gate": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Западные Внутренние Ворота",
            "description": "Западный проем соединяет Проспект Старейшин с периметром и выглядит как разомкнутый шлюз древнего города. По бокам остались гнезда огромных механизмов перехода, но сейчас через них проходят только повозки, носилки и редкие караваны.",
            "background_url": "/static/images/exploration/city/d4/50_52_west_inner_gate.png",
            "environment_tags": ["gate", "defense", "inner_wall", "ruins", "street"],
        },
    },
    (50, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["west"]},
        "content": {
            "title": "Руины Караульной",
            "description": "Небольшой блок у западной стены был пунктом наблюдения за внутренним кольцом, а не простой караульной. Крыша исчезла, но стены стоят идеально ровно; защищенная ниша годится для дома, лавки или будущего поста.",
            "background_url": "/static/images/exploration/city/d4/50_51_guardhouse_plot.png",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "guardhouse", "street"],
        },
    },
    (50, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["west"]},
        "content": {
            "title": "Пустой Арсенал",
            "description": "Встроенная в стену камера сохранила форму арсенала, но не содержимое: все ценное ушло вместе с Исходом или было забрано позже. Пустые пазы в монолите и толстый порог делают место надежным, хотя оно больше похоже на оболочку забытой системы.",
            "background_url": "/static/images/exploration/city/d4/50_53_empty_armory.png",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "armory", "street"],
        },
    },
    # --- Восточная стена ---
    (54, 52): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "is_gate": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Восточные Внутренние Ворота",
            "description": "Восточная арка открывается прямо к Площади Снабжения и держит самый живой поток внутри Круга Исхода. Над проходом тянутся погасшие линии контроля, а грубые настилы и веревочные ограждения лишь помогают людям пользоваться тем, что построено не для них.",
            "background_url": "/static/images/exploration/city/d4/54_52_east_inner_gate.png",
            "environment_tags": ["gate", "defense", "inner_wall", "ruins", "street", "crowd"],
        },
    },
    (54, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["east"]},
        "content": {
            "title": "Торговые Ниши",
            "description": "В восточной стене тянется ряд одинаковых ниш, похожих на древние пункты выдачи снабжения. Их расчистили от обломков, и теперь каждая ячейка может стать лавкой, складом или маленькой мастерской без нарушения монолитной стены.",
            "background_url": "/static/images/exploration/city/d4/54_51_trading_niches.png",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "market_stall", "street"],
        },
    },
    (54, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["east"]},
        "content": {
            "title": "Разрушенное Святилище",
            "description": "Полукруглая площадка у стены выглядит как святилище, хотя ее линии больше похожи на узел настройки портальной сети. Центральная статуя или прибор давно исчезли, а выцветшие рельефы не складываются в читаемые знаки.",
            "background_url": "/static/images/exploration/city/d4/54_53_broken_shrine.png",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "chapel", "street"],
        },
    },
    # --- Угловые Бастионы ---
    (50, 50): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["north", "west"]},
        "visual_overrides": {
            "image_profile": "d4_capital_hub",
            "node_role": "bastion",
            "composition": (
                "a northwest corner bastion encloses a protected empty interior; thick monolith wall geometry and "
                "broken parapets define the scene, with only sparse survivor storage at the edges"
            ),
            "forbidden": ["active soldiers", "standard stone castle keep", "square crop"],
        },
        "content": {
            "title": "Северо-Западный Бастион",
            "description": "Северо-западный бастион — массивный узел внутренней стены, где черный и белый монолит сходятся в толстую угловую оболочку. Купол проломлен, но внутри сухо и тихо; ИИ удерживает это место как один из опорных анкеров стабильного сектора.",
            "background_url": "/static/images/exploration/city/d4/50_50_northwest_bastion.png",
            "environment_tags": ["buildable_plot", "bastion", "inner_wall", "ancient_city", "street"],
        },
    },
    (54, 50): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["north", "east"]},
        "content": {
            "title": "Северо-Восточный Бастион",
            "description": "Северо-восточный бастион дает широкий обзор на внутренний рынок и северную линию стены. Его стены слишком гладкие и толстые для обычной обороны: скорее это был стабилизатор периметра, переживший обвал столицы почти без повреждений.",
            "background_url": "/static/images/exploration/city/d4/54_50_northeast_bastion.png",
            "environment_tags": ["buildable_plot", "bastion", "inner_wall", "ruins", "street"],
        },
    },
    (50, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["south", "west"]},
        "content": {
            "title": "Юго-Западный Бастион",
            "description": "В юго-западном углу стены сходятся под тяжелым углом, образуя сухую защищенную полость. Сейчас здесь складывают материалы и закрывают их тканью, но под временным порядком чувствуется древний узел, рассчитанный на удержание давления извне.",
            "background_url": "/static/images/exploration/city/d4/50_54_southwest_bastion.png",
            "environment_tags": ["buildable_plot", "bastion", "inner_wall", "camp", "street"],
        },
    },
    (54, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["south", "east"]},
        "content": {
            "title": "Юго-Восточный Бастион",
            "description": "Юго-восточный бастион сильнее других тронут внешним влиянием: по белому монолиту ползет темный мох, не разрушая камень, а словно проверяя его границы. Защитная геометрия еще держится, поэтому место подходит для уединенной постройки, но не выглядит полностью спокойным.",
            "background_url": "/static/images/exploration/city/d4/54_54_southeast_bastion.png",
            "environment_tags": ["buildable_plot", "bastion", "inner_wall", "ruins", "street", "overgrowth"],
        },
    },
}
