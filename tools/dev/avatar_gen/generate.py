"""
Avatar image generator — dev tool.

Uses the game's AIService (Gemini) to generate character portraits
and saves them directly into static/images/avatars/<category>/.

Usage:
    # Generate all avatars (both categories, 6 each):
    python -m tools.dev.avatar_gen.generate

    # Generate only feminine avatars:
    python -m tools.dev.avatar_gen.generate --category feminine

    # Generate a single specific avatar:
    python -m tools.dev.avatar_gen.generate --category masculine --index 3

    # Override the prompt seed for a one-off experiment:
    python -m tools.dev.avatar_gen.generate --category feminine --index 1 \
        --prompt-override "Elven ranger with silver hair, forest armor, emerald eyes"

    # Dry-run — print the full prompt without calling the API:
    python -m tools.dev.avatar_gen.generate --dry-run

Run from the project root so imports resolve correctly.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.dev.avatar_gen.prompts import (
    AVATARS_PER_CATEGORY,
    CATEGORY_SEEDS,
    IMAGE_MODEL_KEY,
    NEGATIVE_PROMPT,
    OUTPUT_FORMAT,
    OUTPUT_SIZE,
    STYLE_MASTER,
)

# ── Paths ───────────────────────────────────────────────────────────

AVATARS_DIR = PROJECT_ROOT / "src" / "frontend" / "static" / "images" / "avatars"

CATEGORY_FILENAME_MAP: dict[str, str] = {
    "feminine": "avatar_f",
    "masculine": "avatar_m",
}


# ── Prompt assembly ─────────────────────────────────────────────────


def build_prompt(category: str, index: int, *, override: str | None = None) -> str:
    """Assemble the full generation prompt for a single avatar."""
    if override:
        seed = override
    else:
        seed_template = CATEGORY_SEEDS.get(category)
        if seed_template is None:
            raise ValueError(f"Unknown category: {category!r}. Available: {list(CATEGORY_SEEDS)}")
        seed = seed_template.format(index=index)

    parts = [STYLE_MASTER, seed, NEGATIVE_PROMPT]
    return "\n\n".join(parts)


# ── Generation ──────────────────────────────────────────────────────


async def generate_one(
    category: str,
    index: int,
    *,
    prompt_override: str | None = None,
    dry_run: bool = False,
) -> Path | None:
    """Generate a single avatar image and save to disk. Returns the output path."""
    prompt = build_prompt(category, index, override=prompt_override)
    prefix = CATEGORY_FILENAME_MAP.get(category, f"avatar_{category[0]}")
    filename = f"{prefix}_{index:02d}.png"
    out_dir = AVATARS_DIR / category
    out_path = out_dir / filename

    if dry_run:
        print(f"\n{'='*60}")
        print(f"[DRY RUN] {category}/{filename}")
        print(f"{'='*60}")
        print(prompt)
        print(f"{'='*60}\n")
        return None

    # Late import so --dry-run works without env/dependencies
    from src.backend.config.settings import settings
    from src.backend.core.ai import AIService

    ai = AIService()
    model = getattr(settings, IMAGE_MODEL_KEY, settings.gemini_image_model)

    print(f"  Generating {category}/{filename} with model={model} ...")

    content, content_type = await ai.generate_image_bytes(
        prompt=prompt,
        model=model,
        response_mime_type=OUTPUT_FORMAT,
    )

    if not content:
        print(f"  !! Empty response for {filename}")
        return None

    # Optionally resize via Pillow if available
    try:
        from PIL import Image
        from io import BytesIO

        with Image.open(BytesIO(content)) as img:
            output_img: Image.Image = img.copy()
            if output_img.size != OUTPUT_SIZE:
                resized_img = output_img.resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
                output_img = resized_img
            out_dir.mkdir(parents=True, exist_ok=True)
            output_img.save(out_path, format="PNG")
            print(f"  -> Saved {out_path.relative_to(PROJECT_ROOT)} ({output_img.size[0]}x{output_img.size[1]})")
    except ImportError:
        # No Pillow — save raw bytes
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(content)
        print(f"  -> Saved {out_path.relative_to(PROJECT_ROOT)} (raw, {len(content)} bytes)")

    return out_path


async def generate_batch(
    categories: list[str] | None = None,
    indices: list[int] | None = None,
    *,
    prompt_override: str | None = None,
    dry_run: bool = False,
) -> list[Path]:
    """Generate multiple avatars. Returns list of saved paths."""
    cats = categories or list(CATEGORY_SEEDS)
    idxs = indices or list(range(1, AVATARS_PER_CATEGORY + 1))
    results: list[Path] = []

    total = len(cats) * len(idxs)
    done = 0

    for cat in cats:
        for idx in idxs:
            done += 1
            print(f"[{done}/{total}]", end="")
            path = await generate_one(cat, idx, prompt_override=prompt_override, dry_run=dry_run)
            if path:
                results.append(path)

    return results


# ── CLI ─────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate avatar portraits via the game's AIService (Gemini).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--category", "-c",
        choices=list(CATEGORY_SEEDS),
        help="Generate only this category. Default: all.",
    )
    p.add_argument(
        "--index", "-i",
        type=int,
        help=f"Generate only this index (1..{AVATARS_PER_CATEGORY}). Default: all.",
    )
    p.add_argument(
        "--prompt-override", "-p",
        type=str,
        default=None,
        help="Override the category seed with a custom prompt (style master + negative still applied).",
    )
    p.add_argument(
        "--raw-prompt",
        type=str,
        default=None,
        help="Use this as the COMPLETE prompt, ignoring style master and negative.",
    )
    p.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Print the assembled prompt without calling the API.",
    )
    return p.parse_args()


async def main() -> None:
    args = parse_args()

    categories = [args.category] if args.category else None
    indices = [args.index] if args.index else None

    # --raw-prompt bypasses the template system entirely
    override = args.raw_prompt or args.prompt_override

    print(f"Avatar Generator")
    print(f"  Categories: {categories or 'all'}")
    print(f"  Indices:    {indices or 'all'}")
    print(f"  Output dir: {AVATARS_DIR.relative_to(PROJECT_ROOT)}")
    if override:
        print(f"  Prompt:     [OVERRIDE]")
    if args.dry_run:
        print(f"  Mode:       DRY RUN")
    print()

    results = await generate_batch(
        categories=categories,
        indices=indices,
        prompt_override=override,
        dry_run=args.dry_run,
    )

    if results:
        print(f"\nDone. Generated {len(results)} avatar(s).")
    elif not args.dry_run:
        print("\nNo avatars generated.")


if __name__ == "__main__":
    asyncio.run(main())
