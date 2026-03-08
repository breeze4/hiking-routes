"""
Georef tool - map georeferencing web app.
Run: python3 georef-app/server.py [--images PATH] [--data PATH] [--port N]
Open: http://localhost:8000
"""

import argparse
import sys
from pathlib import Path

# Add package dir to sys.path so all internal imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import settings
from api import images, transform, export, persistence, autotrace, overlay

app = FastAPI()

app.include_router(images.router)
app.include_router(transform.router)
app.include_router(export.router)
app.include_router(persistence.router)
app.include_router(autotrace.router)
app.include_router(overlay.router)

FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


def main():
    parser = argparse.ArgumentParser(description="Georef tool")
    parser.add_argument("--images", default="georef-data/images",
                        help="Path to image directory (default: georef-data/images)")
    parser.add_argument("--data", default="georef-data",
                        help="Path to data directory (default: georef-data)")
    parser.add_argument("--port", type=int, default=8000,
                        help="Server port (default: 8000)")
    args = parser.parse_args()

    settings.image_dir = Path(args.images)
    settings.data_dir = Path(args.data)
    settings.data_dir.mkdir(exist_ok=True)
    settings.port = args.port

    import uvicorn
    print(f"Starting georef tool at http://localhost:{args.port}")
    print(f"  Images: {settings.image_dir}")
    print(f"  Data:   {settings.data_dir}")
    uvicorn.run("server:app", host="127.0.0.1", port=args.port,
                 reload=True, reload_dirs=[str(Path(__file__).resolve().parent)])


if __name__ == "__main__":
    main()
