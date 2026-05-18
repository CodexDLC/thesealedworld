from src.backend.features.world.resources.static.d4_east import STATIC_LOCATIONS as D4_EAST_LOCATIONS
from src.backend.features.world.resources.static.d4_north import STATIC_LOCATIONS as D4_NORTH_LOCATIONS
from src.backend.features.world.resources.static.d4_northeast import STATIC_LOCATIONS as D4_NORTHEAST_LOCATIONS
from src.backend.features.world.resources.static.d4_northwest import STATIC_LOCATIONS as D4_NORTHWEST_LOCATIONS
from src.backend.features.world.resources.static.d4_south import STATIC_LOCATIONS as D4_SOUTH_LOCATIONS
from src.backend.features.world.resources.static.d4_southeast import STATIC_LOCATIONS as D4_SOUTHEAST_LOCATIONS
from src.backend.features.world.resources.static.d4_southwest import STATIC_LOCATIONS as D4_SOUTHWEST_LOCATIONS
from src.backend.features.world.resources.static.d4_types import StaticLocationMap
from src.backend.features.world.resources.static.d4_west import STATIC_LOCATIONS as D4_WEST_LOCATIONS

# ==============================================================================
# СТАТИЧНЫЕ ЛОКАЦИИ: КРУГ ИСХОДА, СТАБИЛЬНЫЙ ЦЕНТР АУР-ЭНТАРА (5x5)
# Сеттинг: древняя техномагическая столица Аур-Энтар вокруг портальной площади Исхода.
# Временные постройки выживших вторичны и не должны вытеснять монолитную архитектуру.
# ==============================================================================
START_VILLAGE_LOCATIONS: StaticLocationMap = {
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
            "title": "Площадь Исхода",
            "description": "Центральная платформа Аур-Энтара лежит под открытым небом: огромный круг из белого и черного монолита, где радиальные каналы сходятся к мертвому портальному ядру. От площади расходятся широкие проходы к северному проспекту, восточному тракту, западной административной линии и южному павильону; бедные палатки и костры жмутся к дальним краям, не перекрывая сам круг.",
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
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Северный Проспект Башни",
            "description": "Северный проспект тянется от Площади Исхода к глухой башне без окон, выточенной из цельного черного монолита. На западе виден вход в тренировочный блок арены, на востоке за стенами проступает торговый зал, а дальше к северу улица упирается в линию внутренних ворот.",
            "environment_tags": ["ancient_tower", "magic_pocket", "ruins", "street", "north_tract"],
        },
    },
    (51, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_arena_main"],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["north", "west"]},
        "content": {
            "title": "Арена Теневого Блока",
            "description": "Северо-западный блок старого города сжат между высокими фасадами черного монолита. Расчищенный вход в арену открыт со стороны северного проспекта; северная и западная стороны упираются в стены корпуса, к югу остается проход к административным зданиям, а восточнее просматривается центральная площадь.",
            "environment_tags": ["arena", "training_block", "ruins", "street", "dark_alley", "monolith", "safe_zone"],
        },
    },
    (53, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_market_hub"],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["north", "east"]},
        "content": {
            "title": "Торговый зал Старого Распорядка",
            "description": "К северу от восточного тракта стоит длинное административное здание с каменными галереями и глубокими нишами. Северная и восточная стороны закрыты стенами корпуса, поэтому входы читаются с южного тракта и западного прохода к Площади Исхода. Внутри уже ставят аукционные доски, временные палатки и первые лавки.",
            "environment_tags": [
                "market",
                "auction",
                "shop_stalls",
                "administrative_hall",
                "ruins",
                "street",
                "safe_zone",
            ],
        },
    },
    # --- Южный сектор ---
    (52, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Южный Приемный Павильон",
            "description": "Южнее площади раскрывается приемный павильон: широкий монолитный зал, боковые арки и потускневшие жилы в ребрах потолка. Северный проход возвращает к портальному кругу, западная сторона смотрит на палату гильдий, а восточнее начинается путь к постоялому двору.",
            "environment_tags": ["ruins", "street", "safe_zone", "reception_pavilion", "monolith_hall"],
        },
    },
    (51, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_town_hall_hub"],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["west", "south"]},
        "content": {
            "title": "Палата Гильдий Старого Реестра",
            "description": "На юго-западной диагонали от Площади Исхода стоит административный корпус с длинными залами учета, закрытыми архивными дверями и нишами под печати. Здесь держат реестр поселения, доски заявок и будущие комнаты гильдий. Западная и южная стороны закрыты стенами корпуса; читаемые проходы идут с севера от западной административной линии и с востока от южного павильона.",
            "environment_tags": [
                "town_hall",
                "administrative_hall",
                "guild_hall",
                "registry",
                "ruins",
                "street",
                "safe_zone",
            ],
        },
    },
    (53, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_tavern_hub"],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["east", "south"]},
        "content": {
            "title": "Постоялый двор Последний Приют",
            "description": "В юго-восточном углу внутреннего кольца стоит крупное здание с десятками бывших служебных комнат. Нижние залы приспособили под постоялый двор: у входа держится теплая таверна, кормчий ведет ключи и пайки. Читаемый выход отсюда идет на север к восточному тракту; южная и восточная стороны закрыты стенами корпуса.",
            "environment_tags": ["tavern", "inn", "rooms", "safe_zone", "street", "monolith_hall", "patched_roof"],
        },
    },
    # --- Западный сектор ---
    (51, 52): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Проспект Старейшин",
            "description": "Западный проспект сложен из плит без швов и держит строгую ось между Площадью Исхода и гражданским ядром старой столицы. Это проход, а не административная палата: к северу виден темный блок арены, к югу начинается палата гильдий, а западная линия выводит к внутренней арке.",
            "environment_tags": ["civic_avenue", "ruins", "street", "paved_road", "safe_zone"],
        },
    },
    # --- Восточный сектор ---
    (53, 52): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": []},
        "content": {
            "title": "Восточный Тракт к Воротам",
            "description": "От Площади Исхода на восток уходит широкая улица старого города, рассчитанная на движение грузов и караванов. Севернее виден торговый зал с аукционными досками и лавками, южнее раскрывается постоялый двор Последний Приют, а дальше на востоке тракт ведет к внутренним воротам.",
            "environment_tags": ["wide_street", "east_tract", "gate_route", "ruins", "street", "safe_zone"],
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
            "description": "Перед северной аркой лежит широкая предвратная площадка у внутренней стены. На юг отсюда уходит северный проспект к Площади Исхода, на запад и восток тянутся проходы вдоль стены, а северный проем выводит за пределы обжитого кольца.",
            "environment_tags": ["gate", "defense", "inner_wall", "ancient_city", "street", "wood_gate"],
        },
    },
    (51, 50): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["north", "south"]},
        "content": {
            "title": "Руины Казарм",
            "description": "Длинный блок у северной стены похож на казармы только для нынешних глаз; раньше это был отсек размещения эвакуационных команд. Северная стена и южный фасад аренного корпуса закрывают вертикальный проход, зато вдоль внутренней стены можно двигаться на запад и восток.",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "barracks", "street"],
        },
    },
    (53, 50): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["north", "south"]},
        "content": {
            "title": "Пустые Загоны",
            "description": "Ряд каменных ячеек у стены напоминает стойла, хотя их гладкая геометрия явно создана не для обычных животных. Северная стена и южный фасад торгового зала закрывают вертикальный проход, а движение остается вдоль внутренней стены к воротам и бастионам.",
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
            "description": "Южный проход ведет к менее обжитым кварталам за внутренним кольцом. Арка свободна, но вдоль ее ребер видны погасшие узлы отсечения: когда-то они могли закрыть сектор без створок и засовов.",
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
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "warehouse", "street"],
        },
    },
    (53, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["north", "south"]},
        "content": {
            "title": "Древний Горн",
            "description": "Высокий горн у южной стены стоит отдельно от постоялого двора: между ними лежит глухой корпус и заваленный разрыв. Пламя давно погасло, но если разбудить контуры, здесь снова можно будет вести производство; проход читается вдоль южной линии стены, а не через северное здание.",
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
            "environment_tags": ["gate", "defense", "inner_wall", "ruins", "street"],
        },
    },
    (50, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["west", "east"]},
        "content": {
            "title": "Руины Караульной",
            "description": "Небольшой блок у западной стены был пунктом наблюдения за внутренним кольцом, а не простой караульной. Западная стена и восточный фасад арены закрывают поперечный проход; вдоль периметра можно идти к северному бастиону или западной арке.",
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
            "description": "Восточный тракт упирается в широкую арку внутренней стены. На запад отсюда идет прямая дорога к Площади Исхода, на север и юг тянется пристенная улица, а восточный проем выводит за пределы обжитого кольца к следующему кварталу. Над аркой видны погасшие линии контроля, внизу разбиты настилы и маленький двор проверки.",
            "environment_tags": ["gate", "defense", "inner_wall", "ruins", "street", "crowd"],
        },
    },
    (54, 51): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["east", "west"]},
        "content": {
            "title": "Торговые Ниши",
            "description": "Улица вдоль восточной стены сужается в ряд торговых ниш: одинаковые каменные проемы уходят в монолит, а перед ними остается длинная полоса мощеного прохода. Восточная стена и западный фасад торгового зала закрывают поперечный проход; движение идет вдоль периметра к арке или северному бастиону.",
            "environment_tags": ["buildable_plot", "inner_wall", "ruins", "market_stall", "street"],
        },
    },
    (54, 53): {
        "sector_id": "D4",
        "is_active": True,
        "services": [],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["east", "west"]},
        "content": {
            "title": "Разрушенное Святилище",
            "description": "Южнее ворот пристенная улица раскрывается в полукруглый карман у восточной стены. На западе стоит глухая сторона постоялого двора, поэтому проход туда не читается; движение идет вдоль стены на север к арке или на юг к угловому двору. Остатки святилища стоят прямо в этом кармане: основание исчезло, рельефы выцвели, вокруг размечены очищенные участки и груды камня.",
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
            "description": "Северо-западный бастион — массивный узел внутренней стены, где черный и белый монолит сходятся в толстую угловую оболочку. Купол проломлен, но внутри сухо и тихо; отсюда южный проход идет к руинам караульной, а восточный выводит вдоль северной стены.",
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
            "description": "В северо-восточном углу бывшего элитного центра пристенная улица входит в бастион, где восточная стена поворачивает в северную и оставляет проход дальше вдоль периметра. Внизу видны очищенные квадраты, кучки обломков и сложенные балки: место уже можно занять под будущую постройку, но сам угол стены остается главным ориентиром.",
            "environment_tags": ["buildable_plot", "bastion", "inner_wall", "ruins", "street"],
        },
    },
    (50, 54): {
        "sector_id": "D4",
        "is_active": True,
        "services": ["svc_blacksmith_repair"],
        "flags": {"is_active": True, "is_safe_zone": True},
        "movement_profile": {"has_road": True, "blocked_exits": ["south", "west"]},
        "content": {
            "title": "Ремесленный Двор Южной Стены",
            "description": "В юго-западном углу внутреннего кольца стены сходятся под тяжелым углом и дают сухой защищенный двор. Здесь уже складывают камень, металл и балки, ставят рабочие столы и будят старый ремонтный горн; вокруг остаются пустые ячейки, которые игроки смогут занять под мастерские, лавки или складские комнаты.",
            "environment_tags": [
                "buildable_plot",
                "bastion",
                "inner_wall",
                "craft_district",
                "workshop",
                "blacksmith",
                "street",
                "safe_zone",
            ],
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
            "description": "На юго-востоке пристенная улица бывшего элитного центра проходит через угловой двор, где восточная стена уходит в южную линию и оставляет выход вдоль периметра. По темному и белому монолиту ползет мох, но внизу еще читаются площадки под застройку, временные навесы и очищенный проход между грудами камня.",
            "environment_tags": ["buildable_plot", "bastion", "inner_wall", "ruins", "street", "overgrowth"],
        },
    },
}


STATIC_LOCATIONS: StaticLocationMap = {
    **START_VILLAGE_LOCATIONS,
    **D4_NORTHWEST_LOCATIONS,
    **D4_NORTH_LOCATIONS,
    **D4_NORTHEAST_LOCATIONS,
    **D4_WEST_LOCATIONS,
    **D4_EAST_LOCATIONS,
    **D4_SOUTHWEST_LOCATIONS,
    **D4_SOUTH_LOCATIONS,
    **D4_SOUTHEAST_LOCATIONS,
}
