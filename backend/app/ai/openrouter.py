import base64
import json
from typing import Any

import httpx

from app.config import get_settings

BASE_URL = "https://openrouter.ai/api/v1"
TIMEOUT_SECONDS = 120.0


class AIError(Exception):
    pass


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = httpx.post(
            f"{BASE_URL}{path}",
            headers={"Authorization": f"Bearer {get_settings().openrouter_api_key}"},
            json=payload,
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AIError(f"OpenRouter request to {path} failed: {exc!r}") from exc


def image_data_url(image: bytes, mime_type: str = "image/jpeg") -> str:
    return f"data:{mime_type};base64,{base64.b64encode(image).decode()}"


def chat_json(
    model: str, prompt: str, schema: dict[str, Any], image: bytes | None = None
) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    if image is not None:
        content.append({"type": "image_url", "image_url": {"url": image_data_url(image)}})
    body = _post(
        "/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "result", "strict": True, "schema": schema},
            },
        },
    )
    try:
        return json.loads(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AIError(f"unexpected chat response: {str(body)[:300]}") from exc


def generate_image(model: str, prompt: str, reference: bytes | None = None) -> bytes:
    payload: dict[str, Any] = {"model": model, "prompt": prompt, "aspect_ratio": "1:1", "n": 1}
    if reference is not None:
        payload["input_references"] = [
            {"type": "image_url", "image_url": {"url": image_data_url(reference)}}
        ]
    body = _post("/images", payload)
    try:
        return base64.b64decode(body["data"][0]["b64_json"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise AIError(f"unexpected image response: {str(body)[:300]}") from exc
