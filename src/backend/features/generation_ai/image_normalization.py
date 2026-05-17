from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO


@dataclass(frozen=True, slots=True)
class NormalizedGeneratedImage:
    content: bytes
    content_type: str
    metadata: dict[str, object]


def normalize_generated_image(
    content: bytes,
    content_type: str,
    *,
    target_content_type: str = "image/webp",
    quality: int = 82,
) -> NormalizedGeneratedImage:
    source_content_type = _normalize_content_type(content_type)
    target_content_type = _normalize_content_type(target_content_type)
    if source_content_type == target_content_type:
        return NormalizedGeneratedImage(
            content=content,
            content_type=source_content_type,
            metadata={
                "image_normalized": False,
                "original_content_type": source_content_type,
                "original_size_bytes": len(content),
            },
        )
    if target_content_type != "image/webp":
        raise RuntimeError(f"Unsupported generated image target content type: {target_content_type}")

    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - dependency is declared in pyproject.
        raise RuntimeError("Pillow is required to normalize generated images") from exc

    with Image.open(BytesIO(content)) as image:
        image.load()
        normalized = image.convert("RGBA") if "A" in image.getbands() else image.convert("RGB")
        output = BytesIO()
        normalized.save(output, format="WEBP", quality=quality, method=6)
        normalized_content = output.getvalue()
        width, height = normalized.size

    return NormalizedGeneratedImage(
        content=normalized_content,
        content_type="image/webp",
        metadata={
            "image_normalized": True,
            "original_content_type": source_content_type,
            "original_size_bytes": len(content),
            "normalized_content_type": "image/webp",
            "normalized_size_bytes": len(normalized_content),
            "normalized_quality": quality,
            "width": width,
            "height": height,
        },
    )


def _normalize_content_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()
