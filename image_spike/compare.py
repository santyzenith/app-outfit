"""Builds out/comparison_*.jpg: one row per photo, original first, then each model."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
MODELS = ["google__gemini-nano-banana-2.1", "openai__gpt-image-2.5-flare", "bytedance-seed__seedream-5-0-flash"]
CELL = 380
HEADER = 26

names = sorted({p.stem for m in MODELS for p in (ROOT / "out" / "gen" / m).glob("*.png")})
for start in range(0, len(names), 4):
    chunk = names[start : start + 4]
    sheet = Image.new("RGB", (CELL * (len(MODELS) + 1), HEADER + CELL * len(chunk)), "white")
    draw = ImageDraw.Draw(sheet)
    for col, label in enumerate(["original"] + [m.split("__")[1] for m in MODELS]):
        draw.text((col * CELL + 8, 7), label, fill="black")
    for row, name in enumerate(chunk):
        source = name.split("@")[0]
        paths = [ROOT / "photos" / f"{source}.jpg"] + [ROOT / "out" / "gen" / m / f"{name}.png" for m in MODELS]
        for col, path in enumerate(paths):
            if not path.exists():
                continue
            img = Image.open(path).convert("RGB")
            img.thumbnail((CELL - 8, CELL - 8))
            sheet.paste(img, (col * CELL + 4, HEADER + row * CELL + 4))
    sheet.save(ROOT / "out" / f"comparison_{start // 4 + 1}.jpg", quality=88)
    print("saved", start // 4 + 1, chunk)
