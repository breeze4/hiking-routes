"""Pydantic models for georef API."""

from pydantic import BaseModel


class GCP(BaseModel):
    px: float
    py: float
    lon: float
    lat: float


class TransformRequest(BaseModel):
    gcps: list[GCP]


class ExportRequest(BaseModel):
    coeffs_lon: list[float]  # [a, b, c]
    coeffs_lat: list[float]  # [d, e, f]
    waypoints: list[dict]    # [{px, py, name}, ...]


class SaveRequest(BaseModel):
    image_name: str
    gcps: list[dict] = []
    waypoints: list[dict] = []
    coeffs_lon: list[float] | None = None
    coeffs_lat: list[float] | None = None
    bounds: list[list[float]] | None = None


class AutoTraceRequest(BaseModel):
    image_name: str
    dark_threshold: int | None = None  # auto-detect if None
    close_kernel: int = 11  # morphological close kernel size, bridges dotted line gaps
    min_area: int = 200
    prune_iterations: int = 20
    simplify_epsilon: float = 3.0
