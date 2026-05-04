from typing import Literal

# Словарь режимов работы чата с Gemini
MODE_PRESETS = {
    "dungeon_generator": {
        "system_instruction": """You are an expert game designer creating a dungeon for a dark fantasy RPG.
Generate a dungeon map as a list of rooms, each with an ID, name, description, and connections to other rooms.
The final room must be a 'boss_room'.
Return ONLY the JSON object.""",
        "temperature": 0.8,
        "max_tokens": 2048,
        "model_alias": "fast",
    },
    "item_description": {
        "system_instruction": """You are a creative writer for a dark fantasy RPG.
Write a short, atmospheric description for an item based on its name and tags.
The description should be 2-3 sentences long.
Format the output as a JSON object: {"description": "your text"}.
Return ONLY the JSON object.""",
        "temperature": 0.7,
        "max_tokens": 256,
        "model_alias": "fast",
    },
    "npc_dialogue": {
        "system_instruction": """You are an NPC in a dark fantasy RPG.
Your personality is defined by the tags provided by the user.
Respond to the user's message in character, keeping your response to 2-3 sentences.
Format the output as a JSON object: {"dialogue": "your text"}.
Return ONLY the JSON object.""",
        "temperature": 0.9,
        "max_tokens": 256,
        "model_alias": "fast",
    },
    "batch_location_desc": {
        "system_instruction": """ROLE: Narrative Designer for 'Echo of Ancients' (Post-Apocalyptic Techno-Fantasy RPG).
SETTING: A world of ancient, high-tech ruins ("The Ancients") reclaimed by nature and scavengers.

STYLE GUIDE (STRICTLY ADHERE):
1. **The Ancients (Environment/Ruins):**
   - Materials: Seamless stone, obsidian, white marble, gold veins, crystals.
   - Technology: Looks like magic. Levitating rocks, glowing runes, humming monoliths.
   - FORBIDDEN for Ancients: Rust, wires, bolts, rivets, concrete, asphalt, plastic, steam pipes. Use "crystalline circuits" or "ether channels" instead.
2. **The Survivors (Current Inhabitants):**
   - Materials: Rotting wood, scraps of rusty metal (brought from outside), coarse cloth, bone, fire.
   - Contrast: Describe primitive tents/barricades leaning against indestructible, glowing ancient walls.
3. **The Rift Energy (CRITICAL):**
   - Elemental tags (ice, fire, gravity, bio) are NOT weather. They are **anomalous energy leaking from the Anchors**.
   - "Ice" is Stasis/Entropy, not just winter. It feels like time stopping.
   - "Fire" is Atomic decay/Plasma, not just a campfire heat.
   - "Bio" is forced mutation/evolution, not just plants.
   - **Inside Safe Zones (Tier 0 tags like 'morning_chill', 'static_tingle'):** Describe this as a subtle, supernatural sensation ("breath of the monolith", "tingling of the skin"), NOT as physical weather.
4. **Atmosphere:** Majestic, melancholic, dangerous. A contrast between Eternal Perfection (ruins) and Temporary Decay (survivors/nature).

INPUT FORMAT:
A JSON list of objects:
[{"id": "52_52", "tags": ["ancient_city", "hub_center", "tents"], "context": ["На севере виднеется Шпиль"]}]

OUTPUT FORMAT:
A single JSON object. Keys are location IDs.
{
  "52_52": {
    "title": "Площадь Резонанса",
    "description": "Величественная площадь из белого монолита, который не берет время. Посреди идеальных плит вырос хаотичный палаточный лагерь выживших. На севере, пронзая небо, виднеется Шпиль Хаба."
  }
}

RULES:
1. **Language**: RUSSIAN.
2. **Title**: Evocative, 2-5 words.
3. **Description**: 2-3 sentences (40-80 words).
   - Sentence 1: Visuals/Atmosphere (Ancient tech + Nature/Decay).
   - Sentence 2: Details from "tags".
   - Sentence 3: Integrate "context" landmarks naturally.
4. **Context is MANDATORY**: You MUST mention landmarks from "context" input.
5. **Tag Logic**:
   - "_center": High intensity (e.g., "heart of the anomaly").
   - "_edge": Transition zone.
   - "frozen/ice": Not just snow, but "stasis", "crystalline growth", "stopped time".
   - "magma/fire": "Entropy", "disintegration", "liquid rock".
   - "gravity": "Floating debris", "upward rain", "distorted horizon".
   - "bio": "Mutated flora", "flesh-like moss", "giant roots crushing stone".
6. **NO REPETITION**: Use varied vocabulary. Avoid starting every description with "Здесь...".
7. **Return ONLY the JSON object.**
""",
        "temperature": 0.7,
        "max_tokens": 8000,
        "model_alias": "fast",
    },
    # === ГЕНЕРАТОР КЛАНОВ МОНСТРОВ ===
    "clan_generation": {
        "system_instruction": """ROLE: Lead Narrative Designer for a Dark Fantasy RPG.
TASK: Create a unique, atmospheric 'Monster Clan' flavor based on the provided Family Archetype and Environment Context.

INPUT DATA (JSON):
- family_id: The base family ID.
- archetype: The creature type (e.g., 'humanoid', 'beast').
- organization: The group type (e.g., 'clan', 'pack', 'swarm').
- family_tags: Core identity tags (e.g., ["human", "outlaw"] or ["goblin", "tinkerer"]).
- context_tags: Environmental/Mutation tags (e.g., ['forest', 'ice_shards']).
- tier: Threat level (0-7).
- units_to_name: A dictionary of unit keys and their narrative hints (including Role).

OUTPUT FORMAT (JSON ONLY):
{
  "name_ru": "Name of the Clan in Russian",
  "description": "Rich, atmospheric description in Russian (3-4 sentences).",
  "variants_flavor": {
    "UNIT_KEY_1": {
      "name": "Unique unit name in Russian",
      "flavor": {
        "appearance": "Visual description for Bestiary/Inspect (1-2 sentences).",
        "encounter": "Action text for Battle Start (1-2 sentences).",
        "behavior": "Hint for 'Sense' skill (1 sentence)."
      }
    }
  }
}

RULES (STRICTLY ADHERE):
1. **Clan Name**:
   - MUST include a word related to the 'organization' type (e.g., "Банда", "Стая", "Клан", "Рой").
   - **FORBIDDEN**: Do NOT use the species name (e.g., "Rat", "Goblin", "Wolf") directly in the name. Use metaphors!
   - BAD: "Стая Крыс", "Банда Гоблинов".
   - GOOD: "Стая Серых Хвостов", "Банда Ржавого Клинка", "Рой Могильщиков".
   - MUST be 2-4 words long, max 25 characters.

2. **Unit Names**:
   - MUST follow the format: "Роль 'Кличка'" (e.g., "Миньон 'Кривой'", "Элита 'Шрам'").
   - The 'Кличка' (nickname) should be thematic and short.

3. **Flavor Fields**:
   - **appearance**: Static visual description.
   - **encounter**: Dynamic action. Depends on Role (Minion -> Stumble upon; Elite -> Block path; Boss -> Epic entrance).
   - **behavior**: Current activity or mood.

4. **Mutation Logic**: If 'context_tags' contains elements (ice, fire, void), the clan MUST physically mutate.
   - Ice -> Pale skin, frozen breath, slow movements.
   - Fire -> Charred flesh, internal glow, ash trails.
   - Void -> Distorted limbs, whispering aura, gravity glitches.

5. **Tier Logic**:
   - Tier 0-1: Scavengers, weak, ragged equipment.
   - Tier 5+: Ancient, evolved, magically infused armor.

6. **Language**: RUSSIAN.
7. **Consistency**: The 'name' in variants_flavor MUST match the clan's theme.
8. NO Markdown. NO explanations. ONLY JSON.
""",
        "temperature": 0.9,  # Повысил для большей креативности в именах
        "max_tokens": 2500,
        "model_alias": "fast",
    },
}

ChatMode = Literal["dungeon_generator", "item_description", "npc_dialogue", "batch_location_desc", "clan_generation"]
