"""Overlay endpoint: returns all images with placement status."""

import json

from fastapi import APIRouter
from PIL import Image

from config import settings
from api.images import _load_labels

router = APIRouter()


@router.get("/api/overlays")
def list_overlays():
    if not settings.image_dir.exists():
        return []

    labels = _load_labels()

    # Index saved data by image stem
    saved = {}
    if settings.data_dir.exists():
        for path in settings.data_dir.glob("*.json"):
            data = json.loads(path.read_text())
            saved[path.stem] = data

    results = []
    for f in sorted(settings.image_dir.iterdir()):
        if f.suffix.lower() not in (".gif", ".jpg", ".png"):
            continue

        with Image.open(f) as img:
            width, height = img.size

        data = saved.get(f.stem, {})
        has_transform = bool(data.get("coeffs_lon") and data.get("coeffs_lat"))

        results.append({
            "image_name": f.name,
            "label": labels.get(f.name, f.name),
            "placed": has_transform,
            "coeffs_lon": data.get("coeffs_lon"),
            "coeffs_lat": data.get("coeffs_lat"),
            "bounds": data.get("bounds"),
            "width": width,
            "height": height,
        })

    return results
