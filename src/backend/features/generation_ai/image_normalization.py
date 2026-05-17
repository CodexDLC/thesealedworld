from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any


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
    target_size: tuple[int, int] | None = None,
    quality: int = 82,
) -> NormalizedGeneratedImage:
    source_content_type = _normalize_content_type(content_type)
    target_content_type = _normalize_content_type(target_content_type)
    if source_content_type == target_content_type and target_size is None:
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
        from PIL import Image, ImageOps
    except ImportError as exc:  # pragma: no cover - dependency is declared in pyproject.
        raise RuntimeError("Pillow is required to normalize generated images") from exc

    with Image.open(BytesIO(content)) as image:
        image.load()
        source_width, source_height = image.size
        normalized = image.convert("RGBA") if "A" in image.getbands() else image.convert("RGB")
        if target_size is not None:
            normalized = ImageOps.fit(
                normalized,
                target_size,
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
        output = BytesIO()
        normalized.save(output, format="WEBP", quality=quality, method=6)
        normalized_content = output.getvalue()
        width, height = normalized.size

    metadata: dict[str, Any] = {
        "image_normalized": True,
        "original_content_type": source_content_type,
        "original_size_bytes": len(content),
        "source_width": source_width,
        "source_height": source_height,
        "normalized_content_type": "image/webp",
        "normalized_size_bytes": len(normalized_content),
        "normalized_quality": quality,
        "width": width,
        "height": height,
    }
    if target_size is not None:
        metadata["target_width"] = target_size[0]
        metadata["target_height"] = target_size[1]
        metadata["target_aspect_ratio"] = round(target_size[0] / target_size[1], 6)

    return NormalizedGeneratedImage(
        content=normalized_content,
        content_type="image/webp",
        metadata=metadata,
    )


def _normalize_content_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()
