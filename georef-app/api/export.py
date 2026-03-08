"""CSV export endpoint."""

from fastapi import APIRouter

from models import ExportRequest

router = APIRouter()


@router.post("/api/export")
def export_csv(req: ExportRequest):
    a, b, c = req.coeffs_lon
    d, e, f = req.coeffs_lat
    lines = ["name,lat,lon"]
    for wp in req.waypoints:
        lon = a * wp["px"] + b * wp["py"] + c
        lat = d * wp["px"] + e * wp["py"] + f
        name = wp.get("name", f"WP{wp.get('idx', 0):03d}")
        lines.append(f"{name},{lat:.6f},{lon:.6f}")
    return {"csv": "\n".join(lines)}
