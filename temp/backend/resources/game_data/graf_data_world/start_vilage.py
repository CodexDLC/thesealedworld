from typing import Any, TypedDict


class _StaticLocationContent(TypedDict):
    title: str
    description: str
    environment_tags: list[str]


class _StaticLocation(TypedDict):
    sector_id: str
    is_active: bool
    services: list[str]
    flags: dict[str, Any]
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
        "flags": {"is_active": True, "is_safe_zone": True, "is_hub": True, "has_road": True},
        "content": {
            "title": "Площадь Рунного Круга",
            "description": "Центр цитадели — древняя площадка из белого камня, который не берет ни время, ни инструменты. Высеченные в полу узоры слабо мерцают. Вокруг этого вечного монолита вырос палаточный лагерь поселенцев — хаос из ткани и дерева на фоне вечности.",
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
        "flags": {"is_active": True, "is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Улица Мудрецов, Башня Испытаний",
            "description": "Мощеная плитами улица ведет к уцелевшей каменной башне без окон. Поселенцы расчистили вход и обнаружили внутри странный пространственный карман. Теперь там Арена — место, где бойцы проверяют свои силы, не боясь разрушить древние стены.",
            "environment_tags": ["ancient_tower", "magic_pocket", "ruins", "street", "arena"],
        },
    },
    (51, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Квартал Теней",
            "description": "Узкие проходы петляют между высокими остовами зданий из черного камня. Здесь темно даже днем. Говорят, в этих руинах мародеры находят тайники Древних, но риск нарваться на неприятности здесь выше.",
            "environment_tags": ["ruins", "debris", "resource_spot", "street", "dark_alley", "monolith"],
        },
    },
    (53, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Руины Библиотеки",
            "description": "Когда-то здесь хранили знания. Теперь древние плиты усыпаны каменной крошкой. Среди обрушенных колонн видны следы свежих раскопок — поселенцы ищут здесь хоть что-то, что поможет понять технологии прошлого.",
            "environment_tags": ["ruins", "debris", "resource_spot", "street", "ancient_knowledge"],
        },
    },
    # --- Южный сектор ---
    (52, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_tavern_hub"],
        "flags": {"is_active": True, "is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Переулок Павших, Таверна",
            "description": "Широкий переулок, где жизнь кипит даже ночью. В первом этаже монументального каменного здания предприимчивые жители открыли таверну 'Последний Приют', заколотив проломы досками. Запах жареного мяса перебивает холод камня.",
            "environment_tags": ["tavern", "ruins", "street", "safe_zone", "lively", "wood_patch"],
        },
    },
    (51, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Заваленный Квартал",
            "description": "Груды гнилых досок и ржавых бочек, принесенных поселенцами, блокируют проход к древним складам. Под этим мусором наверняка скрыто что-то полезное, но завалы придется разбирать вручную.",
            "environment_tags": ["ruins", "debris", "resource_spot", "street", "barrels"],
        },
    },
    (53, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Квартал Ремесленников",
            "description": "Здесь руины носят следы производства: странные остывшие печи и верстаки из неизвестного металла. Новые мастера уже обживают эти места, приспосабливая вечные инструменты под свои нужды.",
            "environment_tags": ["ruins", "debris", "resource_spot", "street", "workshop"],
        },
    },
    # --- Западный сектор ---
    (51, 52): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_town_hall_hub", "svc_blacksmith_repair"],
        "flags": {"is_active": True, "is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Проспект Старейшин",
            "description": "Главная улица, вымощенная плитами без единого шва. В сохранившемся зале заседает Совет поселения. Напротив, в старой оружейной, кузнец раздувает угли в горне, который был построен тысячи лет назад.",
            "environment_tags": ["town_hall", "blacksmith", "ruins", "street", "paved_road"],
        },
    },
    # --- Восточный сектор ---
    (53, 52): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_market_hub"],
        "flags": {"is_active": True, "is_safe_zone": True, "has_road": True},
        "content": {
            "title": "Рыночная Площадь",
            "description": "Улица расширяется, образуя площадь. Среди величественных руин натянуты грязные тенты, а товары разложены прямо на древних постаментах. Это сердце экономики нового поселения.",
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
        "flags": {"is_active": True, "is_safe_zone": False, "is_gate": True, "has_road": True},
        "content": {
            "title": "Северные Внутренние Ворота",
            "description": "Древняя арка в монолитной стене. Родных створок давно нет, вместо них — ворота, сбитые из бревен и металлолома. Стража проверяет всех, кто приходит со стороны пустошей.",
            "environment_tags": ["gate", "defense", "inner_wall", "ancient_city", "street", "wood_gate"],
        },
    },
    (51, 50): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["north"], "has_road": True},
        "content": {
            "title": "Руины Казарм",
            "description": "Остов длинного здания, примыкающего к стене. Крыша обвалилась, но каменные перегородки целы. Если выгрести вековой мусор, здесь можно обустроить отличный склад или жилье.",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "barracks", "street"],
        },
    },
    (53, 50): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["north"], "has_road": True},
        "content": {
            "title": "Пустые Загоны",
            "description": "Каменные стойла у северной стены. Раньше здесь держали зверей Древних, теперь — пустота и ветер. Стена надежно защищает это место с тыла.",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "stable", "street"],
        },
    },
    # --- Южная стена ---
    (52, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": False, "is_gate": True, "has_road": True},
        "content": {
            "title": "Южные Внутренние Ворота",
            "description": "Выход к южным кварталам. Проход в стене свободен, древние механизмы защиты мертвы. Днем здесь кипит жизнь, рабочие таскают материалы из внешних руин.",
            "environment_tags": ["gate", "defense", "inner_wall", "ruins", "street"],
        },
    },
    (51, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["south"], "has_road": True},
        "content": {
            "title": "Руины Склада",
            "description": "Участок у южной стены, заваленный обломками камня. Стена здесь особенно толстая, без единой трещины. Идеальное место для защищенной постройки.",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "warehouse", "street"],
        },
    },
    (53, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["south"], "has_road": True},
        "content": {
            "title": "Древний Горн",
            "description": "Развалины у стены с огромным дымоходом, уходящим ввысь. Горн давно остыл, но сама структура сохранилась идеально. Можно возродить здесь производство.",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "forge", "street"],
        },
    },
    # --- Западная стена ---
    (50, 52): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": False, "is_gate": True, "has_road": True},
        "content": {
            "title": "Западные Внутренние Ворота",
            "description": "Массивный проем, ведущий на Проспект. Это основной путь для доставки грузов. По бокам видны следы креплений каких-то гигантских механизмов, ныне утраченных.",
            "environment_tags": ["gate", "defense", "inner_wall", "ruins", "street"],
        },
    },
    (50, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["west"], "has_road": True},
        "content": {
            "title": "Руины Караульной",
            "description": "Небольшая пристройка к западной стене. Крыши нет, но стены монолитны. Отличное место для дома или лавки, защищенное от ветров.",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "guardhouse", "street"],
        },
    },
    (50, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["west"], "has_road": True},
        "content": {
            "title": "Пустой Арсенал",
            "description": "Укрепленная комната в стене. Двери выбиты, внутри пустота и пыль. Каменный каркас не пострадал от времени, готовый служить новым хозяевам.",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "armory", "street"],
        },
    },
    # --- Восточная стена ---
    (54, 52): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": False, "is_gate": True, "has_road": True},
        "content": {
            "title": "Восточные Внутренние Ворота",
            "description": "Арка, выходящая прямо на Рыночную Площадь. Здесь всегда толчея, стража лениво наблюдает за потоком людей среди древних камней.",
            "environment_tags": ["gate", "defense", "inner_wall", "ruins", "street", "crowd"],
        },
    },
    (54, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["east"], "has_road": True},
        "content": {
            "title": "Торговые Ниши",
            "description": "Ряд ниш, выдолбленных прямо в восточной стене. Место расчищено от обломков и готово принять торговцев или стать фундаментом.",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "market_stall", "street"],
        },
    },
    (54, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["east"], "has_road": True},
        "content": {
            "title": "Разрушенное Святилище",
            "description": "Полукруглый фундамент у стены, где когда-то стояла статуя. Стена украшена выцветшей резьбой. Тихое место для постройки.",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "chapel", "street"],
        },
    },
    # --- Угловые Бастионы ---
    (50, 50): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["north", "west"], "has_road": True},
        "content": {
            "title": "Северо-Западный Бастион",
            "description": "Массивная угловая башня из серого монолита. Внутри сухо, несмотря на разрушенный купол. Самое надежное убежище в цитадели.",
            "environment_tags": ["buildable_plot", "bastion", "inner_wall", "ancient_city", "street"],
        },
    },
    (54, 50): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["north", "east"], "has_road": True},
        "content": {
            "title": "Северо-Восточный Бастион",
            "description": "Угловая башня с широким обзором. Стены здесь невероятно толстые. Отличное место для тех, кто ценит безопасность превыше всего.",
            "environment_tags": ["buildable_plot", "bastion", "inner_wall", "ruins", "street"],
        },
    },
    (50, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["south", "west"], "has_road": True},
        "content": {
            "title": "Юго-Западный Бастион",
            "description": "Основание угловой башни, превращенное жителями в склад. Стены цитадели сходятся здесь, создавая идеальную защиту от ветров.",
            "environment_tags": ["buildable_plot", "bastion", "inner_wall", "camp", "street"],
        },
    },
    (54, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True, "restricted_exits": ["south", "east"], "has_road": True},
        "content": {
            "title": "Юго-Восточный Бастион",
            "description": "Руины башни, поросшие странным мхом. Каменная кладка выглядит вечной. Хорошее место для уединенного дома.",
            "environment_tags": ["buildable_plot", "bastion", "inner_wall", "ruins", "street", "overgrowth"],
        },
    },
}
