from __future__ import annotations

NO_TEXT_IMAGE_CONTRACT = "\n".join(
    [
        "No visible text contract:",
        "The generated image must contain no letters, no words, no numbers, no readable or pseudo-readable symbols.",
        "Do not render signs, labels, captions, posters, title cards, document pages, UI text, logos, watermarks, signatures, glyphs, or runes.",
        "All supplied names, titles, slugs, and descriptions are private metadata for visual mood only; never draw them as text in the image.",
    ]
)


def apply_no_text_image_contract(prompt: str) -> str:
    value = prompt.strip()
    if not value:
        return NO_TEXT_IMAGE_CONTRACT
    if NO_TEXT_IMAGE_CONTRACT in value:
        return value
    return f"{value}\n\n{NO_TEXT_IMAGE_CONTRACT}"
