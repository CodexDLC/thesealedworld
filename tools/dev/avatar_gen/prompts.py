"""
Avatar generation prompt templates.

Edit STYLE_MASTER, CATEGORY_SEEDS, and per-category negative prompts here,
then run `generate.py` to produce images via the game's AIService (Gemini).

The system prompt (STYLE_MASTER) sets the artistic baseline.
Each category (feminine / masculine) has a SEED that describes the subject,
and an optional NEGATIVE that excludes unwanted elements.

You can override everything per run via CLI flags — see generate.py --help.
"""

# ── Master style prompt ─────────────────────────────────────────────
# Shared across ALL avatar categories. Describes the artistic direction,
# medium, rendering quality, framing, and palette.

STYLE_MASTER = (
    "Dark fantasy character portrait, painterly RPG art, warm amber key-light "
    "on a deep charcoal background, head-and-shoulders framing, "
    "centered composition facing 3/4 view, strong rim light, "
    "highly detailed face and armor, muted earth-tone palette with gold accents, "
    "1024×1024 square aspect ratio, no text, no UI elements, no watermark."
)

# ── Category seeds ──────────────────────────────────────────────────
# One per avatar style category. Each seed is appended after STYLE_MASTER.
# Index suffix (_01 .. _06) is added automatically by the generator.

CATEGORY_SEEDS: dict[str, str] = {
    "feminine": (
        "A determined female warrior of a post-apocalyptic fantasy world, "
        "angular cheekbones, battle-worn light armor with engraved shoulder plates, "
        "dark braided hair with ember-coloured streaks, calm intense gaze, "
        "subtle scars across brow. Variation {index}: unique hairstyle, unique armor trim, "
        "unique facial expression."
    ),
    "masculine": (
        "A battle-hardened male warrior of a post-apocalyptic fantasy world, "
        "strong jaw, weathered face, rugged plate-and-leather armor with scratched insignia, "
        "short cropped hair or shaved head, stoic determined eyes, "
        "old scar across cheek or nose. Variation {index}: unique hair, unique armor style, "
        "unique facial expression."
    ),
}

# ── Negative prompts ────────────────────────────────────────────────
# Appended with "Negative:" prefix. Helps Gemini avoid common artifacts.

NEGATIVE_PROMPT = (
    "Negative: blurry, low quality, text overlay, watermark, signature, logo, "
    "full body shot, hands visible, background clutter, anime style, cartoon, "
    "chibi, oversaturated, neon colors, modern clothing, real photo, "
    "deformed face, extra fingers, duplicate, cropped frame."
)

# ── Output config ───────────────────────────────────────────────────

IMAGE_MODEL_KEY = "gemini_avatar_image_model"
OUTPUT_SIZE = (1024, 1024)
OUTPUT_FORMAT = "image/png"
AVATARS_PER_CATEGORY = 6
