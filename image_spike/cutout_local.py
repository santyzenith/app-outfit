"""Baseline: local background removal for every photo in photos/ -> out/cutout/."""

from pathlib import Path

from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).parent
OUT = ROOT / "out" / "cutout"
OUT.mkdir(parents=True, exist_ok=True)

session = new_session("isnet-general-use")
for photo in sorted((ROOT / "photos").glob("*.jpg")):
    result = remove(Image.open(photo).convert("RGB"), session=session)
    result.save(OUT / f"{photo.stem}.png")
    print("done", photo.name)
