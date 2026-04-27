"""
Модуль содержит JSON-схему и требования к формату для генерации подземелий
с помощью модели Gemini.

Определяет структуру и правила для генерируемых данных,
обеспечивая их консистентность и соответствие игровым механикам.
"""

DUNGEON_JSON_SCHEMA_PROMPT = """
FORMAT REQUIREMENTS:
Your response MUST be a single, raw JSON object without any explanations or text outside the JSON.
No Markdown.

CRITICAL LANGUAGE RULE:
All user-facing creative strings (dungeon_meta.name, rooms.name, rooms.description, 
and all text "values" in the "exits" object) MUST be generated in RUSSIAN.

JSON Schema:
{
  "dungeon_meta": {
    "name": str (The name of the Shard, in RUSSIAN, based on the TASK Theme),
    "level": int (The level number, taken from the TASK),
    "meta_rooms": {
      "start": str (The Room ID of the starting room),

      // Include "end" OR "transition" (but not both)
      "transition": str (The Room ID for the exit to the next level)
      // "end": str (The Room ID for a dead-end boss room)
    }
  },
  "rooms": {
    "UNIQUE_ROOM_ID": {
      "name": str (The name of the room, in RUSSIAN, e.g. "Арсенал"),
      "description": str (Atmospheric description, in RUSSIAN. MUST NOT mention enemies, loot, traps, or objects.),
      "environment_tags": list[str] (An array of tags, CHOSEN ONLY from the "Allowed Environment Tags" in the TASK),
      "exits": dict[str, str] (Object where "key" is the target Room ID,
                                 and "value" is the button text, in RUSSIAN.
                                 e.g. {"room_2": "Пройти в темный Арсенал"})
    }
    // ... repeat for all 10 rooms ...
  }
}

Key Requirements:
1.  Generate exactly 10 rooms.
2.  "rooms" MUST be an OBJECT (dict), not an array.
3.  All Room IDs used in "meta_rooms" and as "keys" in "exits" MUST exist as top-level keys in the "rooms" object.
4.  The location MUST be "connected" (all rooms must be reachable from "meta_rooms.start").
5.  "description" MUST NOT mention any interactive objects (enemies, loot, chests, levers).
6.  "environment_tags" MUST be chosen STRICTLY from the "Allowed Environment Tags" list provided in the TASK.
7.  The location MUST be "bi-directional". (If "room_1" has an exit to "room_2", then "room_2" MUST have an exit back to "room_1").
8.  Exit Text Consistency: The button text (the "value" in "exits") MUST be thematically consistent with the "name" of the target room (the "key").
    (GOOD: {"room_2": "Enter the Armory"} -> "name": "The Armory")
    (BAD: {"room_2": "Go to the Library"} -> "name": "The Armory")
9.  Non-Linearity (Junctions): The shard MUST be non-linear. At least 2 (two) rooms must have 2 or more exits.
10. Branching Limit: NO single room may have more than 3 (three) exits (i.e., the "exits" dict cannot have more than 3 key-value pairs).
11. Dead Ends: The shard MUST contain at least 1 (one) "dead-end" room (that is NOT "meta_rooms.start") which has only 1 (one) exit.
"""
