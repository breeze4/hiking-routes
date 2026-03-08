"""Affine transform computation endpoint."""

import math

import numpy as np
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from models import TransformRequest

router = APIRouter()


@router.post("/api/transform")
def compute_transform(req: TransformRequest):
    if len(req.gcps) < 3:
        return JSONResponse({"error": "need at least 3 GCPs"}, status_code=400)

    n = len(req.gcps)
    A = np.zeros((n, 3))
    b_lon = np.zeros(n)
    b_lat = np.zeros(n)

    for i, g in enumerate(req.gcps):
        A[i] = [g.px, g.py, 1.0]
        b_lon[i] = g.lon
        b_lat[i] = g.lat

    coeffs_lon, _, _, _ = np.linalg.lstsq(A, b_lon, rcond=None)
    coeffs_lat, _, _, _ = np.linalg.lstsq(A, b_lat, rcond=None)

    residuals = []
    for i, g in enumerate(req.gcps):
        pred_lon = coeffs_lon[0] * g.px + coeffs_lon[1] * g.py + coeffs_lon[2]
        pred_lat = coeffs_lat[0] * g.px + coeffs_lat[1] * g.py + coeffs_lat[2]
        err_lon = pred_lon - g.lon
        err_lat = pred_lat - g.lat
        cos_lat = math.cos(math.radians(g.lat))
        err_m = math.sqrt((err_lat * 111000) ** 2 + (err_lon * 111000 * cos_lat) ** 2)
        residuals.append({
            "idx": i,
            "err_lon": round(err_lon, 7),
            "err_lat": round(err_lat, 7),
            "err_meters": round(err_m, 1),
        })

    return {
        "coeffs_lon": [round(c, 12) for c in coeffs_lon.tolist()],
        "coeffs_lat": [round(c, 12) for c in coeffs_lat.tolist()],
        "residuals": residuals,
    }
