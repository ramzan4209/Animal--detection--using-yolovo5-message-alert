import base64
import io
import json
import os
import requests
from PIL import Image
import config

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"

PROMPT = """You are verifying an automated wildlife-corridor camera detection.

YOLOv5 reported these detections:
{yolo}

Look at the image yourself and answer ONLY with JSON, no other text:
{{
  "humans": <number of people you see>,
  "domestic_animals": [{{"type": "cow|buffalo|goat|sheep|horse|dog|other", "count": <n>}}],
  "wild_animals": [{{"type": "<species>", "count": <n>}}],
  "agrees_with_yolo": true or false,
  "corrections": "<what YOLO got wrong, or empty string>",
  "risk_level": "low|medium|high",
  "summary": "<one short sentence for an alert message>"
}}

Notes: YOLO cannot tell buffalo from cow, so decide that yourself.
Risk is high if wild animals and humans or livestock are close together."""


def _image_b64(path):
    img = Image.open(path).convert("RGB")
    img.thumbnail((1568, 1568))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def verify(image_path, detections):
    key = os.getenv("GEMINI_API_KEY", "")
    if not key or key.startswith("your_"):
        return {"status": "skipped", "reason": "GEMINI_API_KEY not set in .env"}

    yolo_text = json.dumps(
        [{"label": d["label"], "confidence": d["confidence"]} for d in detections]
    ) if detections else "nothing detected"

    body = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": _image_b64(image_path)}},
                {"text": PROMPT.format(yolo=yolo_text)},
            ]
        }],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    headers = {"x-goog-api-key": key, "content-type": "application/json"}

    try:
        resp = requests.post(URL.format(MODEL), headers=headers, json=body, timeout=60)
        if not resp.ok:
            return {"status": "error", "reason": f"API error {resp.status_code}: {resp.text[:200]}"}
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = text.replace("```json", "").replace("```", "").strip()
        result = json.loads(text)
        result["status"] = "ok"
        return result
    except Exception as e:
        return {"status": "error", "reason": type(e).__name__}
