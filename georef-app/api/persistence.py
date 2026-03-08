"""Save/load state endpoints."""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from config import settings
from models import SaveRequest

router = APIRouter()


@router.post("/api/save")
def save_data(req: SaveRequest):
    settings.data_dir.mkdir(exist_ok=True)
    path = settings.data_dir / f"{Path(req.image_name).stem}.json"
    data = {
        "image_name": req.image_name,
        "gcps": req.gcps,
        "waypoints": req.waypoints,
        "coeffs_lon": req.coeffs_lon,
        "coeffs_lat": req.coeffs_lat,
        "bounds": req.bounds,
    }
    data["saved_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, indent=2))
    return {"ok": True, "saved_at": data["saved_at"]}


@router.get("/api/load/{image_name}")
def load_data(image_name: str):
    path = settings.data_dir / f"{Path(image_name).stem}.json"
    if not path.exists():
        return {"gcps": [], "waypoints": [], "coeffs_lon": None, "coeffs_lat": None, "saved_at": None}
    data = json.loads(path.read_text())
    data.setdefault("saved_at", None)
    return data
