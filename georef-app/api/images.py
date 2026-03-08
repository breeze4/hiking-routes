"""Image listing and serving endpoints."""

import csv

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from config import settings

router = APIRouter()


def _load_labels() -> dict[str, str]:
    """Load filename -> label mapping from image-rename.csv in data dir."""
    csv_path = settings.data_dir / "image-rename.csv"
    if not csv_path.exists():
        return {}
    labels = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            labels[row["new"]] = row["label"]
    return labels


@router.get("/api/images")
def list_images():
    if not settings.image_dir.exists():
        return []
    labels = _load_labels()
    files = sorted(
        f.name for f in settings.image_dir.iterdir()
        if f.suffix.lower() in (".gif", ".jpg", ".png")
    )
    return [{"name": f, "label": labels.get(f, f)} for f in files]


@router.get("/api/image/{name}")
def get_image(name: str):
    path = settings.image_dir / name
    if not path.exists() or not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    media = {"gif": "image/gif", "jpg": "image/jpeg", "png": "image/png"}
    ext = path.suffix.lower().strip(".")
    return FileResponse(path, media_type=media.get(ext, "application/octet-stream"))
