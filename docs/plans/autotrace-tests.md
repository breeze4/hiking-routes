# Autotrace: Fix Pipeline + Build Test Library

## Context

The autotrace processing pipeline in `georef-app/processing/autotrace.py` is missing two critical algorithm steps from the plan (`docs/plans/autotrace.md`):
1. **Morphological close** — bridges gaps in dotted/dashed lines. Without it, dotted lines on overview maps (page_194) fragment into tiny components that get filtered out. Currently finds 3 routes instead of expected 7.
2. **Border aspect ratio filter** — catches thin border strips that flood fill misses.
3. **`close_kernel` parameter** — not exposed in model, API, or frontend.

After fixing the pipeline, build a test library that generates an HTML report showing the full pipeline visualization (original image -> binary mask -> final overlay with route legend) for each test image.

---

## Part 1: Fix Processing Pipeline

### Files to modify

- `georef-app/processing/autotrace.py` — add morphological close + border filter
- `georef-app/models.py` — add `close_kernel` param to `AutoTraceRequest`
- `georef-app/api/autotrace.py` — forward `close_kernel` param
- `georef-app/frontend/index.html` — add "Bridge gaps" input
- `georef-app/frontend/js/autotrace.js` — read and send `close_kernel`

### Changes

1. **`processing/autotrace.py` — `extract_routes()`**: After `cv2.threshold`, before `_remove_borders`, add morphological close with elliptical kernel. Add `close_kernel: int = 11` parameter. Skip if close_kernel <= 1.

2. **`processing/autotrace.py` — border filter**: In the component loop, after computing stats, skip components where aspect ratio (max(w,h)/min(w,h)) > 20 AND bounding box is within 5px of any image edge.

3. **`models.py`**: Add `close_kernel: int = 11` to `AutoTraceRequest`.

4. **`api/autotrace.py`**: Forward `req.close_kernel` to `extract_routes()`.

5. **`frontend/index.html`**: Add bridge gaps input between threshold and min area.

6. **`frontend/js/autotrace.js`**: Read `at-bridge` value, send as `close_kernel` in request body.

---

## Part 2: Build Test Library

### New files

- `georef-app/tests/test_autotrace.py` — test runner script (CLI)
- Output HTML is generated, gitignored

### Design

A standalone Python script that:

1. Discovers all GIF/PNG images in the configured image directory
2. Runs `extract_routes()` with default params on each
3. Generates three visualizations per image:
   - **Original**: the source image
   - **Binary mask**: thresholded + morphologically closed binary (white on black)
   - **Overlay**: original with detected route polylines in distinct colors
4. Generates a single self-contained HTML report with:
   - One section per image, three views side by side
   - Legend below each overlay: color swatch, route ID, point count, path length
   - Summary stats at top

### Implementation details

- Add `extract_routes_debug()` to `processing/autotrace.py` — same pipeline but also returns the binary mask after close step
- Use `cv2.polylines` for overlay drawing on a copy of the original
- Colors match frontend: `#ff6600, #ff00cc, #00ccff, #ccff00, #ff3333, #33ff99`
- Images embedded as base64 data URIs — single HTML file, no external assets
- CLI: `python3 georef-app/tests/test_autotrace.py [--images DIR] [--output FILE]`
- Defaults: images=`html/stevens-canyon/images`, output=`tmp/autotrace_report.html`

---

## Checklist

- [x] 1. Add morphological close step to `extract_routes()` with `close_kernel` parameter
- [x] 2. Add border aspect ratio filter to component loop
- [x] 3. Add `close_kernel` to `AutoTraceRequest` model, API endpoint, frontend HTML + JS
- [x] 4. Verify pipeline on page_194 (6 routes, 4 substantial), page_195 (13/7), page_204 (7/2)
- [x] 5. Add `_debug=True` mode to `extract_routes()` returning routes + binary mask
- [x] 6. Build test runner script with HTML report generation (3-stage viz + legend)
- [x] 7. Run report — 16 images, 48 visualizations, 112 legend rows, 19MB self-contained HTML
