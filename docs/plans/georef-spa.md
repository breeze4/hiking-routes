# Georef App - SPA Restructuring Plan

## Context

`georef.py` is a ~1027-line single-file FastAPI app with inline HTML/JS/CSS. It works but won't scale — the user plans to add significant functionality over time. This plan restructures it into `georef-app/` with clean frontend/backend separation, using the same patterns the project already uses (`canyoneering-app/` as precedent).

No new features — pure restructuring. The tool continues to produce CSV for CalTopo.

## Target Structure

```
georef-app/
  server.py                    # FastAPI entry point, mounts routers + static files
  config.py                    # Settings (image dir, data dir, port) via argparse
  models.py                    # All Pydantic models
  api/
    __init__.py
    images.py                  # GET /api/images, GET /api/image/{name}
    transform.py               # POST /api/transform
    export.py                  # POST /api/export
    persistence.py             # POST /api/save, GET /api/load/{name}
    autotrace.py               # POST /api/autotrace
  processing/
    __init__.py
    autotrace.py               # OpenCV pipeline (pure computation, no web deps)
  frontend/
    index.html                 # Shell HTML with module script tag
    css/
      style.css                # Extracted from inline <style>
    js/
      app.js                   # Entry point: init, image loading, mode switching
      api.js                   # All fetch() wrappers (single place for endpoint URLs)
      canvas.js                # Canvas rendering, pan/zoom, draw hooks
      gcp.js                   # GCP placement, commit, undo, transform UI
      trace.js                 # Waypoint placement, undo, CSV export
      autotrace.js             # Auto-trace detection UI, accept/reject
      persistence.js           # Save/load, dirty tracking, keyboard shortcuts
```

## Key Design Decisions

**Static serving:** `server.py` mounts `StaticFiles(directory="frontend", html=True)` at `/` after registering API routers. Single server, no proxy needed.

**Config:** CLI argparse in `server.py` — `--images PATH` (default: `html/stevens-canyon/images`), `--data PATH` (default: `georef-data`), `--port N` (default: 8000). `config.py` holds a module-level settings object that API modules import.

**Frontend shared state:** Canvas module uses a draw-hook pattern to avoid circular deps:
- `canvas.js` exports `onDraw(fn)` and `onCanvasClick(mode, fn)`
- `gcp.js`, `trace.js`, `autotrace.js` register their draw callbacks and click handlers
- No module needs to import from a module that imports from it

**What happens to existing files:**
- `georef.py` — deleted after migration (git history preserves it)

## Implementation Checklist

- [x] 1. **Scaffold directory + config + models.** Create `georef-app/` directory structure, `config.py` with Settings class (argparse), `models.py` with all 5 Pydantic models from `georef.py`. Create `__init__.py` files. Verify: `python3 -c "from georef_app.config import settings"` imports cleanly.

- [x] 2. **Extract processing module.** Move the 6 OpenCV functions (`_auto_threshold`, `_remove_borders`, `_morphological_thin`, `_prune_branches`, `_find_longest_path`, `extract_routes`) to `georef-app/processing/autotrace.py`. No API code. Verify: import succeeds.

- [x] 3. **Create API routers + server.py.** Create the 5 router files under `api/`, each as a `FastAPI APIRouter`. Create `server.py` that includes all routers, mounts static files at `frontend/`, runs uvicorn with argparse. Create a minimal `frontend/index.html` placeholder. Verify: `python3 georef-app/server.py` starts, `GET /api/images` returns the image list.

- [x] 4. **Extract HTML + CSS.** Create `frontend/index.html` with the sidebar/canvas HTML structure (no inline styles, no inline script). Create `frontend/css/style.css` with all styles extracted verbatim. Add `<script type="module" src="js/app.js">`. Verify: page loads with correct layout, no JS yet.

- [x] 5. **Extract `api.js` + `canvas.js` + `app.js`.** `api.js`: all fetch wrappers. `canvas.js`: canvas setup, draw() with hook system, pan/zoom handlers, screenToImage(). `app.js`: imports modules, loads image list, wires up image selector. Verify: page loads, image displays, pan/zoom works.

- [x] 6. **Extract `gcp.js`.** GCP click handler, commitGCP(), undoGCP(), updateGCPTable(), computeTransform(). Registers draw hook for GCP markers. Verify: GCP mode works end-to-end including transform computation and residuals.

- [x] 7. **Extract `trace.js` + `autotrace.js`.** Waypoint placement, undo, table, exportCSV(). Auto-trace: runAutoTrace(), accept/reject routes, route list UI. Verify: trace mode works, auto-trace works, CSV export produces correct output.

- [x] 8. **Extract `persistence.js`.** Save/load state, isDirty tracking, updateSaveStatus(), keyboard shortcuts (g/t mode switch, Ctrl+Z undo, Ctrl+S save). Verify: save/load round-trips correctly, unsaved changes warning works.

- [x] 9. **Cleanup.** Delete `georef.py` from repo root. Update `docs/SPEC.md` with new `georef-app/` structure. Update `.gitignore` if needed. Verify: `python3 georef-app/server.py` is the only way to run the tool, full workflow works (load image -> place GCPs -> compute transform -> trace -> export CSV).

## Files Modified

- `georef.py` — source (read then delete)
- `docs/SPEC.md` — update georef tool section
- `.gitignore` — verify `georef-data/` entry
- All new files under `georef-app/`

## Verification

1. `python3 georef-app/server.py`, open http://localhost:8000
2. Select a map image from dropdown
3. Place 3+ GCPs, compute transform, check residuals
4. Switch to trace mode, place waypoints along route
5. Export CSV — verify `name,lat,lon` output
6. Save state, reload page, load state — verify persistence
7. Run auto-trace on a map with route lines, accept a detected route
