# Hiking Routes - Project Spec

## Georeferencing Tool (`georef-app/`)

A local web app for extracting route coordinates from scanned topo map images.

### Purpose
The book maps (from Canyoneering 3) are scanned USGS 7.5-minute topo quads with hand-drawn route overlays. This tool lets you:
1. Set ground control points (GCPs) on a map image by clicking known features and entering their lat/lon
2. Compute an affine transformation from pixel coordinates to geographic coordinates
3. Trace the drawn route by clicking along it
4. Export route coordinates as CSV (`name,lat,lon`) for the CalTopo extension

### Running
```
python3 georef-app/server.py [--images PATH] [--data PATH] [--port N]
```
Defaults: images from `html/stevens-canyon/images/`, data in `georef-data/`, port 8000.

### Architecture
SPA with clean frontend/backend separation:
- **Backend:** FastAPI server (`server.py`) with modular API routers (`api/`) and image processing (`processing/`)
- **Frontend:** Vanilla ES modules (`frontend/js/`), no build step
- **Config:** CLI argparse for image dir, data dir, port
- Affine transform via numpy least-squares (6 params: pixel x,y -> lat,lon)
- GCPs come from named features, elevation spot heights, or UTM grid intersections on the USGS quads
- State persisted to `georef-data/{image_name}.json`

### Auto-trace
Automatic route detection from map images using OpenCV. The pipeline:
1. Auto-threshold to isolate the darkest drawn features (routes, text, arrows) from lighter contour lines
2. Flood-fill border removal to eliminate image frame artifacts
3. Connected component analysis to find candidate route regions
4. Morphological thinning (hit-or-miss skeletonization) to get 1px centerlines
5. Branch pruning to strip text label stubs and arrow tips
6. Double-BFS to find the longest path through each skeleton (the route)
7. Douglas-Peucker simplification to reduce to manageable waypoint count

Detected routes appear as colored overlays on the canvas. User can accept (converts to waypoints) or reject each detection. Tunable parameters: threshold, min component area, prune iterations, simplification epsilon.

### Overlay View

A composite map view (`/overlay.html`) that overlays all georeferenced book map images onto an interactive Leaflet map with USGS topo tiles. Each image is positioned using its computed affine transform (bounding box derived from the 4 image corners).

Features:
- Per-image visibility toggle and opacity slider
- Click-to-place labeled points with auto-calculated lat/lon
- CSV export (`name,lat,lon`) for the CalTopo extension
- Uses the same backend and `georef-data/` JSON files as the main georef tool

### First target
Stevens Canyon / Baker Route (Hikes 21 & 22): 7 detailed topo maps across 4 USGS quads (King Mesa, Stevens Canyon South, Stevens Canyon North, Scorpion Gulch).

