"""One-time script to generate the account page background image via AIService."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PROMPT = (
    "Dark fantasy environment artwork for a web application background. "
    "An ancient sealed vault interior with tall stone arches and faintly glowing amber runes carved into the walls. "
    "Soft golden-orange light seeps through cracks in a massive sealed door in the distance, "
    "casting warm volumetric light rays through dust particles. "
    "The color palette blends deep charcoal grays (#0a0a0c) with warm amber (#ffaa00) and muted violet (#7744ff) accents. "
    "Atmospheric, ethereal, painterly style. No characters, no text, no UI elements. "
    "Subtle fog hugs the ground. Suitable as a tiled or stretched website background with a dark overlay on top. "
    "Wide aspect ratio, 1920x1080 composition."
)

OUTPUT_DIR = ROOT / "src" / "frontend" / "static" / "images" / "account"
OUTPUT_FILE = OUTPUT_DIR / "bg.webp"


async def main() -> None:
    from src.backend.core.ai import AIService

    ai = AIService()
    if ai.provider is None:
        print("ERROR: Gemini API key not configured. Set GEMINI_API_KEY in .env")
        sys.exit(1)

    print("Generating account background image...")
    print(f"Prompt: {PROMPT[:120]}...")

    content, content_type = await ai.generate_image_bytes(
        PROMPT,
        response_mime_type="image/webp",
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_bytes(content)
    print(f"Saved: {OUTPUT_FILE} ({len(content):,} bytes, {content_type})")


if __name__ == "__main__":
    asyncio.run(main())
