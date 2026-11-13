"""Split the two Gemini sprite sheets into usable PNG assets.

Run from the repository root:
    python tools/extract_art_sheets.py

The source sheets stay untouched. The sprite sheet is a 4x5 grid (20 poses);
the office environment sheet is a 3x3 grid (9 scenes). Sprite backgrounds are
removed with edge-connected flood fill so enclosed dark details are preserved.
"""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SPRITE_SHEET = ASSETS / "Gemini_Generated_Image_f889qsf889qsf889.jpg"
SCENE_SHEET = ASSETS / "Gemini_Generated_Image_f889qsf889qsf889 (1).jpg"

SPRITE_COLS, SPRITE_ROWS = 4, 5
SCENE_COLS, SCENE_ROWS = 3, 3
# RGB distance threshold from the sampled sheet background. Only pixels
# connected to a cell edge are removed; dark suit/outline pixels stay intact.
BACKGROUND_TOLERANCE = 25


def cell_bounds(size: tuple[int, int], cols: int, rows: int, col: int, row: int):
    width, height = size
    left = round(col * width / cols)
    top = round(row * height / rows)
    right = round((col + 1) * width / cols)
    bottom = round((row + 1) * height / rows)
    return left, top, right, bottom


def color_distance(a, b) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]))


def remove_edge_background(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    px = rgba.load()
    width, height = rgba.size
    corners = [px[0, 0], px[width - 1, 0], px[0, height - 1], px[width - 1, height - 1]]
    bg = tuple(sorted(c[i] for c in corners)[len(corners) // 2] for i in range(3))

    visited = bytearray(width * height)
    queue = deque()

    def add(x: int, y: int):
        index = y * width + x
        if visited[index]:
            return
        visited[index] = 1
        if color_distance(px[x, y], bg) <= BACKGROUND_TOLERANCE:
            queue.append((x, y))

    for x in range(width):
        add(x, 0)
        add(x, height - 1)
    for y in range(height):
        add(0, y)
        add(width - 1, y)

    while queue:
        x, y = queue.popleft()
        r, g, b, _ = px[x, y]
        px[x, y] = (r, g, b, 0)
        if x: add(x - 1, y)
        if x + 1 < width: add(x + 1, y)
        if y: add(x, y - 1)
        if y + 1 < height: add(x, y + 1)

    return rgba


def main() -> None:
    if not SPRITE_SHEET.is_file() or not SCENE_SHEET.is_file():
        missing = [str(p) for p in (SPRITE_SHEET, SCENE_SHEET) if not p.is_file()]
        raise FileNotFoundError("Missing source sheet(s): " + ", ".join(missing))

    sprite_source = Image.open(SPRITE_SHEET).convert("RGB")
    scene_source = Image.open(SCENE_SHEET).convert("RGB")

    sprite_dir = ASSETS / "characters" / "neoburi" / "frames"
    scene_dir = ASSETS / "backgrounds" / "scenes"
    sprite_dir.mkdir(parents=True, exist_ok=True)
    scene_dir.mkdir(parents=True, exist_ok=True)

    sprite_manifest = []
    for row in range(SPRITE_ROWS):
        for col in range(SPRITE_COLS):
            number = row * SPRITE_COLS + col + 1
            crop = sprite_source.crop(cell_bounds(sprite_source.size, SPRITE_COLS, SPRITE_ROWS, col, row))
            frame = remove_edge_background(crop)
            # Pad uneven integer grid cells to one shared canvas so every pose
            # has the same dimensions and can be swapped without layout jumps.
            frame_canvas = Image.new("RGBA", (
                (sprite_source.width + SPRITE_COLS - 1) // SPRITE_COLS,
                (sprite_source.height + SPRITE_ROWS - 1) // SPRITE_ROWS,
            ), (0, 0, 0, 0))
            frame_canvas.alpha_composite(frame, (0, 0))
            frame = frame_canvas
            name = f"pose_{number:02d}.png"
            frame.save(sprite_dir / name, optimize=True)
            sprite_manifest.append({
                "file": name, "row": row, "column": col,
                "canvas_width": frame.width, "canvas_height": frame.height,
                "note": "Cell crop; inspect alignment before animation."
            })

    scene_manifest = []
    for row in range(SCENE_ROWS):
        for col in range(SCENE_COLS):
            number = row * SCENE_COLS + col + 1
            crop = scene_source.crop(cell_bounds(scene_source.size, SCENE_COLS, SCENE_ROWS, col, row))
            scene_canvas = Image.new("RGB", (
                (scene_source.width + SCENE_COLS - 1) // SCENE_COLS,
                (scene_source.height + SCENE_ROWS - 1) // SCENE_ROWS,
            ), (0, 0, 0))
            scene_canvas.paste(crop, (0, 0))
            crop = scene_canvas
            name = f"scene_{number:02d}.png"
            crop.save(scene_dir / name, optimize=True)
            scene_manifest.append({
                "file": name, "row": row, "column": col,
                "width": crop.width, "height": crop.height
            })

    (sprite_dir / "manifest.json").write_text(
        json.dumps(sprite_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (scene_dir / "manifest.json").write_text(
        json.dumps(scene_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Extracted {len(sprite_manifest)} character cells to {sprite_dir}")
    print(f"Extracted {len(scene_manifest)} environment cells to {scene_dir}")
    print("Source sheets were not modified. Review frame alignment and transparency before wiring animation.")


if __name__ == "__main__":
    main()
