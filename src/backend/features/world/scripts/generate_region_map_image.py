from __future__ import annotations

import argparse
import asyncio
from io import BytesIO
from pathlib import Path

from PIL import Image

from src.backend.config.settings import settings
from src.backend.core.ai import AIService
from src.backend.features.generation_ai.asset_storage import build_generated_asset_storage

D4_REGION_MAP_PROMPT = """Generate a square 4K master map asset for a dark fantasy MMORPG region, designed to be sliced into a 15x15 game grid later.

Create a large ruined ancient capital city occupying almost the entire square image area, not a small isolated settlement. The city may have an irregular outline but should broadly fill the canvas with dense streets, plazas, ruined elite quarters, wall-side districts, empty buildable foundations, rubble yards, courtyards, service pockets, old ceremonial avenues, and broken monolith infrastructure.

Setting: Aur-Entar, former elite center of an ancient technomagical capital in a sealed world. Style: ancient sacred technomagical architecture, black and white seamless monolith stone, weathered dark grey surfaces, restrained pale stone highlights, faint ether-gold veins embedded in stone, overcast cool lighting, solemn dark survival fantasy, painterly realistic tactical map concept art.

Composition requirements:
- top-down / slightly elevated orthographic tactical city map
- square format
- city fills the image as much as possible
- outer city walls form the main perimeter
- four clear large exits/gates roughly north, east, south, and west
- central walled inner elite sector around a ruined portal plaza
- inner sector has two readable internal gates/exits
- main streets connect the inner sector to the outer gates
- major landmarks sit well inside broad map zones so a later 15x15 grid overlay will not cut every important landmark exactly on a border
- include corner bastions, broken wall segments, streets radiating to the center, market-like plaza areas, a tavern/refuge-like warm occupied courtyard, an arena/trial tower landmark, library ruins, shrine pocket, artisan/forge quarter, warehouse yards, and many empty claimable plots/foundations

Strict negatives:
No UI. No grid lines. No labels. No letters. No numbers. No readable text. No icons. No markers. No compass. No border frame. No characters, no people, no creatures. Do not make a collage or board-game tile sheet. This is one coherent city map background asset for later slicing and SVG marker overlay."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a manual region master map image.")
    parser.add_argument("--region-id", default="D4")
    parser.add_argument("--model", default="gemini-3-pro-image-preview")
    parser.add_argument("--aspect-ratio", default="1:1")
    parser.add_argument("--image-size", default="4K", choices=("1K", "2K", "4K"))
    parser.add_argument("--content-type", default="image/png")
    parser.add_argument("--storage-key", default="world/maps/d4/d4_region_master_4k.png")
    parser.add_argument("--prompt-file", default="")
    return parser.parse_args()


async def async_main(args: argparse.Namespace | None = None) -> None:
    options = args or parse_args()
    prompt = _load_prompt(options.prompt_file)
    ai = AIService()
    content, content_type = await ai.generate_image_bytes(
        prompt,
        model=options.model,
        response_mime_type=options.content_type,
        image_config={
            "aspect_ratio": options.aspect_ratio,
            "image_size": options.image_size,
        },
    )
    if not isinstance(content, bytes) or not content:
        raise RuntimeError("Region map generation returned empty image content")

    width, height = _image_size(content)
    storage = build_generated_asset_storage(settings)
    ref = await storage.put_bytes(
        storage_key=options.storage_key,
        content=content,
        content_type=content_type or options.content_type,
        metadata={
            "region_id": options.region_id,
            "model": options.model,
            "aspect_ratio": options.aspect_ratio,
            "requested_image_size": options.image_size,
            "width": width,
            "height": height,
        },
    )
    print(
        f"region map generated region_id={options.region_id} storage_key={ref.storage_key} "
        f"url={ref.public_url} content_type={ref.content_type} size={width}x{height} bytes={ref.size_bytes}"
    )


def _load_prompt(prompt_file: str) -> str:
    if not prompt_file:
        return D4_REGION_MAP_PROMPT
    return Path(prompt_file).read_text(encoding="utf-8")


def _image_size(content: bytes) -> tuple[int, int]:
    with Image.open(BytesIO(content)) as image:
        return image.size


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
