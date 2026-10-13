"""Generative test: recreate each garment photo as a clean catalog image via OpenRouter."""

import argparse
import base64
import io
import json
import sys
import time
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).parent
OUT = ROOT / "out" / "gen"
LEDGER = ROOT / "out" / "costs.jsonl"
ENV_FILE = ROOT.parent / "app_outfit_backend" / ".env"

SINGLE_PROMPT = (
    "This is a casual photo of a clothing item taken by its owner. Recreate exactly this same "
    "item as a clean e-commerce catalog photo: the item alone, front view, neatly laid flat and "
    "unwrinkled, evenly lit, centered, on a plain pure white background. No hanger, no person, "
    "no furniture, no props. Preserve exactly the original colors, fabric texture, pattern, "
    "logos, prints, text, buttons, zippers, stitching and proportions. Do not add, remove or "
    "redesign anything. If the item is footwear, show the pair side by side."
)

ONE_OF_MANY_PROMPT = (
    "This photo shows several clothing items. Recreate ONLY this one: {item}. Show exactly that "
    "same item as a clean e-commerce catalog photo: the item alone, front view, neatly laid flat "
    "and unwrinkled, evenly lit, centered, on a plain pure white background. No other items, no "
    "hanger, no person, no furniture. Preserve exactly its original colors, fabric texture, "
    "pattern, logos, prints, buttons and proportions. Do not add, remove or redesign anything."
)


def api_key() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("OPENROUTER_API_KEY not found")


def spent() -> float:
    if not LEDGER.exists():
        return 0.0
    return sum(json.loads(line)["cost"] for line in LEDGER.read_text().splitlines() if line)


def data_url(photo: Path) -> str:
    img = Image.open(photo).convert("RGB")
    img.thumbnail((1024, 1024))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def generate_images_api(
    client: httpx.Client, model: str, photo: Path, prompt: str, out_path: Path
) -> dict:
    started = time.time()
    payload = {
        "model": model,
        "prompt": prompt,
        "input_references": [{"type": "image_url", "image_url": {"url": data_url(photo)}}],
        "aspect_ratio": "1:1",
        "resolution": "1K",
        "n": 1,
    }
    if model.startswith("openai/"):
        payload["quality"] = "medium"
    response = client.post("https://openrouter.ai/api/v1/images", json=payload)
    seconds = round(time.time() - started, 1)
    body = response.json()
    if response.status_code != 200 or not body.get("data"):
        return {"ok": False, "seconds": seconds, "cost": 0.0, "error": json.dumps(body)[:400]}

    cost = float((body.get("usage") or {}).get("cost") or 0.0)
    item = body["data"][0]
    raw = base64.b64decode(item["b64_json"]) if item.get("b64_json") else httpx.get(item["url"]).content
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.open(io.BytesIO(raw)).save(out_path)
    return {"ok": True, "seconds": seconds, "cost": cost, "usage": body.get("usage")}


def generate(client: httpx.Client, model: str, photo: Path, prompt: str, out_path: Path) -> dict:
    if not model.startswith("google/"):
        return generate_images_api(client, model, photo, prompt, out_path)
    started = time.time()
    response = client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={
            "model": model,
            "modalities": ["image", "text"],
            "image_config": {"aspect_ratio": "1:1"},
            "usage": {"include": True},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url(photo)}},
                    ],
                }
            ],
        },
    )
    seconds = round(time.time() - started, 1)
    body = response.json()
    if response.status_code != 200 or "choices" not in body:
        return {"ok": False, "seconds": seconds, "cost": 0.0, "error": json.dumps(body)[:400]}

    cost = float((body.get("usage") or {}).get("cost") or 0.0)
    images = body["choices"][0]["message"].get("images") or []
    if not images:
        text = str(body["choices"][0]["message"].get("content"))[:300]
        return {"ok": False, "seconds": seconds, "cost": cost, "error": "no image: " + text}

    encoded = images[0]["image_url"]["url"].split(",", 1)[1]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.open(io.BytesIO(base64.b64decode(encoded))).save(out_path)
    return {"ok": True, "seconds": seconds, "cost": cost}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", required=True)
    parser.add_argument("--photos", nargs="+", required=True)
    parser.add_argument("--item", help="describe one item to extract from a multi-garment photo")
    parser.add_argument("--suffix", default="")
    parser.add_argument("--budget", type=float, default=0.95)
    args = parser.parse_args()

    client = httpx.Client(headers={"Authorization": f"Bearer {api_key()}"}, timeout=180)
    prompt = ONE_OF_MANY_PROMPT.format(item=args.item) if args.item else SINGLE_PROMPT

    for model in args.models:
        for name in args.photos:
            if spent() >= args.budget:
                sys.exit(f"budget reached: {spent():.3f}")
            photo = ROOT / "photos" / f"{name}.jpg"
            out_path = OUT / model.replace("/", "__") / f"{name}{args.suffix}.png"
            if out_path.exists():
                continue
            try:
                result = generate(client, model, photo, prompt, out_path)
            except httpx.HTTPError as exc:
                result = {"ok": False, "seconds": None, "cost": 0.0, "error": repr(exc)}
            LEDGER.parent.mkdir(parents=True, exist_ok=True)
            with LEDGER.open("a") as ledger:
                ledger.write(json.dumps({"model": model, "photo": name + args.suffix, **result}) + "\n")
            print(model, name, result, f"total={spent():.3f}", flush=True)


if __name__ == "__main__":
    main()
