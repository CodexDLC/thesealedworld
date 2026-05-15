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
    content: _StaticLocationContent


# ==============================================================================
# СТАТИЧНЫЕ ЛОКАЦИИ: ЦИТАДЕЛЬ (ВНУТРЕННИЙ ГОРОД 5x5)
# Сеттинг: Древние Руины (Монолит), заселенные выжившими (Палатки/Мусор)
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
        "content": {
            "title": "Площадь Рунного Круга",
            "description": "Центр цитадели — древняя площадка из белого камня, который не берет ни время, ни инструменты. Высеченные в полу узоры слабо мерцают. Вокруг этого вечного монолита вырос палаточный лагерь поселенцев — хаос из ткани и дерева на фоне вечности.",
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
            "title": "Улица Мудрецов, Башня Испытаний",
            "description": "Мощеная плитами улица ведет к уцелевшей каменной башне без окон. Поселенцы расчистили вход и обнаружили внутри странный пространственный карман. Теперь там Арена — место, где бойцы проверяют свои силы, не боясь разрушить древние стены.",
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
            "description": "Узкие проходы петляют между высокими остовами зданий из черного камня. Здесь темно даже днем. Говорят, в этих руинах мародеры находят тайники Древних, но риск нарваться на неприятности здесь выше.",
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
            "description": "Когда-то здесь хранили знания. Теперь древние плиты усыпаны каменной крошкой. Среди обрушенных колонн видны следы свежих раскопок — поселенцы ищут здесь хоть что-то, что поможет понять технологии прошлого.",
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
        "content": {
            "title": "Переулок Павших, Таверна",
            "description": "Широкий переулок, где жизнь кипит даже ночью. В первом этаже монументального каменного здания предприимчивые жители открыли таверну 'Последний Приют', заколотив проломы досками. Запах жареного мяса перебивает холод камня.",
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
            "description": "Груды гнилых досок и ржавых бочек, принесенных поселенцами, блокируют проход к древним складам. Под этим мусором наверняка скрыто что-то полезное, но завалы придется разбирать вручную.",
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
            "description": "Здесь руины носят следы производства: странные остывшие печи и верстаки из неизвестного металла. Новые мастера уже обживают эти места, приспосабливая вечные инструменты под свои нужды.",
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
            "description": "Главная улица, вымощенная плитами без единого шва. В сохранившемся зале заседает Совет поселения. Напротив, в старой оружейной, кузнец раздувает угли в горне, который был построен тысячи лет назад.",
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
        "content": {
            "title": "Рыночная Площадь",
            "description": "Улица расширяется, образуя площадь. Среди величественных руин натянуты грязные тенты, а товары разложены прямо на древних постаментах. Это сердце экономики нового поселения.",
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
        "content": {
            "title": "Северные Внутренние Ворота",
            "description": "Древняя арка в монолитной стене. Родных створок давно нет, вместо них — ворота, сбитые из бревен и металлолома. Стража проверяет всех, кто приходит со стороны пустошей.",
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
            "description": "Остов длинного здания, примыкающего к стене. Крыша обвалилась, но каменные перегородки целы. Если выгрести вековой мусор, здесь можно обустроить отличный склад или жилье.",
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
            "description": "Каменные стойла у северной стены. Раньше здесь держали зверей Древних, теперь — пустота и ветер. Стена надежно защищает это место с тыла.",
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
            "description": "Выход к южным кварталам. Проход в стене свободен, древние механизмы защиты мертвы. Днем здесь кипит жизнь, рабочие таскают материалы из внешних руин.",
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
            "description": "Участок у южной стены, заваленный обломками камня. Стена здесь особенно толстая, без единой трещины. Идеальное место для защищенной постройки.",
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
            "description": "Развалины у стены с огромным дымоходом, уходящим ввысь. Горн давно остыл, но сама структура сохранилась идеально. Можно возродить здесь производство.",
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
            "description": "Массивный проем, ведущий на Проспект. Это основной путь для доставки грузов. По бокам видны следы креплений каких-то гигантских механизмов, ныне утраченных.",
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
            "description": "Небольшая пристройка к западной стене. Крыши нет, но стены монолитны. Отличное место для дома или лавки, защищенное от ветров.",
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
            "description": "Укрепленная комната в стене. Двери выбиты, внутри пустота и пыль. Каменный каркас не пострадал от времени, готовый служить новым хозяевам.",
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
            "description": "Арка, выходящая прямо на Рыночную Площадь. Здесь всегда толчея, стража лениво наблюдает за потоком людей среди древних камней.",
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
            "description": "Ряд ниш, выдолбленных прямо в восточной стене. Место расчищено от обломков и готово принять торговцев или стать фундаментом.",
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
            "description": "Полукруглый фундамент у стены, где когда-то стояла статуя. Стена украшена выцветшей резьбой. Тихое место для постройки.",
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
        "content": {
            "title": "Северо-Западный Бастион",
            "description": "Массивная угловая башня из серого монолита. Внутри сухо, несмотря на разрушенный купол. Самое надежное убежище в цитадели.",
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
            "description": "Угловая башня с широким обзором. Стены здесь невероятно толстые. Отличное место для тех, кто ценит безопасность превыше всего.",
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
            "description": "Основание угловой башни, превращенное жителями в склад. Стены цитадели сходятся здесь, создавая идеальную защиту от ветров.",
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
            "description": "Руины башни, поросшие странным мхом. Каменная кладка выглядит вечной. Хорошее место для уединенного дома.",
            "background_url": "/static/images/exploration/city/d4/54_54_southeast_bastion.png",
            "environment_tags": ["buildable_plot", "bastion", "inner_wall", "ruins", "street", "overgrowth"],
        },
    },
}
