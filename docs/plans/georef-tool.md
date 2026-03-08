# Map Georeferencing Tool - Stevens Canyon MVP

## Context

The hiking-routes project has 7 scanned USGS topo map images for Stevens Canyon (Hikes 21 & 22) with hand-drawn route overlays. The goal is to extract route coordinates from these images and push them to CalTopo, then correlate the rich route description text with positions along the route.

This is a validation exercise: build the simplest thing that works, try it on Stevens Canyon, and see if it's useful before investing more.

## Approach: Local Web App (`georef.py`)

A single Python file serving a local web app via FastAPI (already installed). No new dependencies needed -- uses fastapi, uvicorn, numpy, PIL (all available). The entire UI is inline HTML/JS/CSS in the Python file.

### Why a web app instead of matplotlib
- No matplotlib installed, no X11 display on WSL2
- Canvas zoom/pan is smoother than matplotlib
- CSV output can be copy-pasted directly into the CalTopo extension
- Browser is always available via WSL2

## How It Works

### Georeferencing Workflow
1. Run `python3 georef.py`, open browser to `localhost:8000`
2. Select a map image from dropdown (auto-discovers GIFs in `html/stevens-canyon/images/`)
3. **GCP mode**: Click known points on the map, enter their lat/lon. Need 3+ ground control points.
4. Hit "Compute Transform" -- shows per-point residual error so you can spot bad GCPs
5. **Trace mode**: Click along the drawn route to place numbered waypoints
6. Hit "Export CSV" -- transforms pixel coords to lat/lon, shows copyable `name,lat,lon` CSV
7. Paste CSV into CalTopo extension, or use a direct-post button

### Where GCP coordinates come from
- **Named features**: Stevens Arch, Crack-in-the-Wall, Fortymile Ridge Trailhead -- look up on CalTopo's topo layer
- **Elevation spot heights**: Points labeled "5087T" etc. on the map -- cross-reference with CalTopo/USGS National Map
- **UTM grid intersections**: The grid lines on USGS quads are 1000m UTM lines with values printed at edges

### The math
Affine transform (6 parameters) maps pixel coordinates to lat/lon:
- `lon = a*px + b*py + c`
- `lat = d*px + e*py + f`
- Solved via `numpy.linalg.lstsq` from 3+ GCP pairs
- This works because the maps are flat scans of USGS quads (conformal projection, small area = effectively linear)

### Map images to process (7 detailed maps)
| File | Content | USGS Quad |
|---|---|---|
| page_195_img_1.gif | Map 25: Crack-in-the-Wall, Coyote Gulch | Stevens Canyon S |
| page_200_img_1.gif | Map 26: Upper Stevens / Baker Trail | Stevens Canyon S |
| page_204_img_1.gif | Map 27: Waterpocket Fold / descent | Stevens Canyon N |
| page_206_img_1.gif | Map 28: Georges Camp Canyon | Stevens Canyon N |
| page_208_img_1.gif | Map 29: Escalante River / Yurt Dome | Scorpion Gulch |
| page_210_img_1.gif | Map 30: Fools Canyon / King Mesa | King Mesa |
| page_216_img_1.gif | Hike 22: Fold/Shofar Canyon | Stevens Canyon N |

Plus 2 overview maps (page_188, page_194) that can optionally be georeferenced using named features.

## Files

```
georef.py              -- Web app for georeferencing and route tracing
georef-data/           -- Saved state per map image (gitignored)
docs/SPEC.md           -- Add georef tool to project spec
.gitignore             -- Add georef-data/
```

## Implementation Checklist

- [ ] 1. Create `docs/SPEC.md` with the georef tool spec, add `georef-data/` to `.gitignore`

- [ ] 2. Create `georef.py` with FastAPI skeleton -- serves a page at localhost:8000, auto-discovers GIF images in `html/stevens-canyon/images/`, serves them at `/api/image/{name}`. Verify: page loads, image list appears.

- [ ] 3. Add the HTML/JS canvas UI -- inline HTML with: image dropdown, canvas element, zoom/pan (mouse wheel + drag). Selecting an image loads and displays it on the canvas. Verify: can view and navigate map images in browser.

- [ ] 4. Add GCP mode -- click canvas to place red marker + number. Input fields for lat/lon appear. GCPs shown in a table. Undo removes last GCP. Verify: can place and see GCPs on map.

- [ ] 5. Add affine transform computation -- `/api/transform` endpoint takes GCP pixel/geo pairs, returns coefficients + per-point residuals via numpy.linalg.lstsq. UI calls this on button click, shows residuals in GCP table (green/red based on error magnitude). Verify: residuals are reasonable with test GCPs.

- [ ] 6. Add trace mode -- toggle between GCP/Trace modes. Trace clicks add blue numbered waypoints. Editable waypoint names. Undo. Verify: can trace along a route.

- [ ] 7. Add CSV export -- `/api/export` transforms waypoint pixels to lat/lon using computed coefficients, returns `name,lat,lon` CSV. Shows in copyable textarea. Verify: export produces valid coordinates.

- [ ] 8. Add save/load persistence -- GCPs and traces saved to `georef-data/{image_name}.json`. Auto-loaded when image is selected. Verify: reload page, GCPs persist.


## Verification

1. Run `python3 georef.py`, open browser
2. Load page_195_img_1.gif (Crack-in-the-Wall area)
3. Place 4+ GCPs using known features (look up coords on CalTopo)
4. Compute transform, verify residuals < 0.001 degrees (~100m)
5. Trace the Hike 21 route through the map
6. Export CSV, paste into CalTopo extension on the Stevens Canyon map
7. Visually verify route points land on correct terrain in CalTopo
