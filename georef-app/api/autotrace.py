"""Auto-trace endpoint."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from config import settings
from models import AutoTraceRequest
from processing.autotrace import extract_routes

router = APIRouter()


@router.post("/api/autotrace")
def autotrace(req: AutoTraceRequest):
    image_path = str(settings.image_dir / req.image_name)
    if not Path(image_path).exists():
        return JSONResponse({"error": "image not found"}, status_code=404)
    routes = extract_routes(
        image_path,
        dark_threshold=req.dark_threshold,
        close_kernel=req.close_kernel,
        min_area=req.min_area,
        prune_iterations=req.prune_iterations,
        simplify_epsilon=req.simplify_epsilon,
    )
    return {"routes": routes, "threshold_used": req.dark_threshold or "auto"}
