"""Georef app configuration. Populated from CLI args at startup."""

from pathlib import Path


class Settings:
    image_dir: Path = Path("georef-data/images")
    data_dir: Path = Path("georef-data")
    port: int = 8000


settings = Settings()
