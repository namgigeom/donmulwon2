"""Extract one clean, static Neoburi character with transparent background.

The source is a 4x5 pose sheet. Pose 16 (row 4, column 4) is selected because
it contains only the seated raccoon: no desk, monitor, chair, or office props.
Run from the repository root with: python tools/extract_art_sheets.py
"""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "Gemini_Generated_Image_f889qsf889qsf889.jpg"
OUTPUT = ROOT / "assets" / "characters" / "neoburi" / "neoburi.png"
POSE_COLUMNS = 4
POSE_ROWS = 5
POSE_NUMBER = 16
BACKGROUND_TOLERANCE = 25


def remove_edge_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    corners = [pixels[0, 0], pixels[width - 1, 0],
               pixels[0, height - 1], pixels[width - 1, height - 1]]
    background = tuple(sorted(c[i] for c in corners)[len(corners) // 2]
                       for i in range(3))
    visited = bytearray(width * height)
    queue = deque()

    def add(x: int, y: int):
        index = y * width + x
        if visited[index]:
            return
        visited[index] = 1
        color = pixels[x, y]
        if max(abs(color[i] - background[i]) for i in range(3)) <= BACKGROUND_TOLERANCE:
            queue.append((x, y))

    for x in range(width):
        add(x, 0)
        add(x, height - 1)
    for y in range(height):
        add(0, y)
        add(width - 1, y)

    while queue:
        x, y = queue.popleft()
        r, g, b, _ = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
        if x > 0: add(x - 1, y)
        if x + 1 < width: add(x + 1, y)
        if y > 0: add(x, y - 1)
        if y + 1 < height: add(x, y + 1)
    return rgba


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Character source sheet not found: {SOURCE}")

    with Image.open(SOURCE) as source:
        source = source.convert("RGB")
        index = POSE_NUMBER - 1
        row, column = divmod(index, POSE_COLUMNS)
        left = round(column * source.width / POSE_COLUMNS)
        top = round(row * source.height / POSE_ROWS)
        right = round((column + 1) * source.width / POSE_COLUMNS)
        bottom = round((row + 1) * source.height / POSE_ROWS)
        character = remove_edge_background(source.crop((left, top, right, bottom)))

    alpha = character.getchannel("A")
    bounds = alpha.getbbox()
    if bounds is None:
        raise RuntimeError("Background removal produced an empty character image")

    # Trim all transparent margins and retain a tiny transparent breathing room.
    character = character.crop(bounds)
    margin = 4
    trimmed = Image.new("RGBA", (character.width + margin * 2,
                                  character.height + margin * 2), (0, 0, 0, 0))
    trimmed.alpha_composite(character, (margin, margin))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    trimmed.save(OUTPUT, optimize=True)

    manifest = {
        "file": OUTPUT.name,
        "source_pose": POSE_NUMBER,
        "source_row": row + 1,
        "source_column": column + 1,
        "background": "transparent",
        "contains_furniture": False,
        "animated": False,
        "width": trimmed.width,
        "height": trimmed.height,
    }
    (OUTPUT.parent / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Extracted one static transparent Neoburi character: {OUTPUT}")
    print(f"Image size: {trimmed.width}x{trimmed.height}; source pose: {POSE_NUMBER}")
    print("No office background, desk, monitor, or animation frames are used.")


if __name__ == "__main__":
    main()
