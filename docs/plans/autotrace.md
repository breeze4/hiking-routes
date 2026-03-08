# Auto-Trace: Automatic Feature Detection from Topo Maps

## Context

The georef tool needs to detect drawn lines (routes, roads, drainages) on scanned topo map images. The goal is aggressive feature detection — find everything that looks like a drawn line, present all candidates to the user, and let them cherry-pick which are real routes.

## Two Map Types

### Detailed topo maps (page_195, 200, 204, 206, 208, 210, 216)
- Scanned USGS 7.5-minute quads with route overlays
- Route lines are **solid black**, 2-5px wide at darkest intensity
- GIF palette: route/text pixels at intensity ~0-7, contour lines at ~105+, background at 230+
- Clear intensity gap between drawn features and contour lines

### Overview/hand-drawn maps (page_188, page_194)
- Hand-drawn with legend showing different line styles
- Routes are **dotted lines** — 1px dots with 5-19px gaps between them
- Roads are dashed, drainage is thin dotted
- GIF palette: evenly spaced intensity levels (0, 17, 34, 51...), no clear gap

## Proven Algorithm

### Pipeline
```
1. Load grayscale image
2. Auto-threshold to capture darkest ~5% of pixels
3. Binary threshold (THRESH_BINARY_INV)
4. Morphological CLOSE to bridge gaps between dots/dashes (kernel size ~11px)
5. FloodFill from border pixels to remove image frame artifacts
6. Filter out border-like artifacts (aspect ratio > 20 AND near image edge)
7. Connected components analysis
8. For each component with area > min_area:
   a. Morphological thinning (hit-or-miss with 8 structuring elements)
   b. Prune short branches (iteratively remove endpoints)
   c. Find longest path via double-BFS
   d. Simplify via Douglas-Peucker (cv2.approxPolyDP)
   e. Record as candidate with pixel coordinates
9. Return ALL candidates sorted by path length
```

### Key Technical Details

**Auto-threshold:** Capture the darkest 5% of pixels. This is generous enough for both map types. For detailed maps it gets routes+text+arrows. For overview maps it gets all drawn lines.

**Morphological closing (critical for dotted lines):** `cv2.morphologyEx(binary, MORPH_CLOSE, kernel)` with an elliptical kernel. Size 11 bridges gaps up to ~5px in each direction. This connects dotted line segments into continuous features. Without this, dotted lines fragment into hundreds of tiny 1px components.

**Border removal:** FloodFill from every border pixel, not margin masking. Margin masking cuts routes that approach the image edge. FloodFill only removes components physically connected to the border. Additionally filter components with aspect ratio > 20 that touch near the edge (catches thin border strips the flood fill misses).

**Morphological thinning (no scikit-image needed):** Iterative hit-or-miss with 8 standard structuring elements (4 edge + 4 corner, each rotated). Converges in 2-5 iterations on these images since features are already thin. Uses `cv2.MORPH_HITMISS` which is available in base OpenCV.

```python
elements = []
e1 = np.array([[-1,-1,-1],[0,1,0],[1,1,1]], dtype=np.int8)
e2 = np.array([[0,-1,-1],[1,1,-1],[0,1,0]], dtype=np.int8)
for _ in range(4):
    elements.append(e1.copy())
    elements.append(e2.copy())
    e1 = np.rot90(e1)
    e2 = np.rot90(e2)
```

**Branch pruning:** Iteratively remove pixels with exactly 1 neighbor (endpoints). Each pass peels one pixel off every branch tip. N passes removes branches up to N pixels long. Text label stubs and arrow tips are typically 5-20px, so 10 passes is a good default. This separates route spines from attached text without needing OCR.

**Longest path via double-BFS:** Build pixel adjacency graph (8-connected), find endpoints (1 neighbor). BFS from any endpoint to find farthest point, then BFS from there. The path between the two farthest points is the main route through that component. This handles branch points cleanly — always picks the trunk, ignoring stubs.

**Douglas-Peucker simplification:** `cv2.approxPolyDP(pts, epsilon, closed=False)`. Epsilon ~2.0 reduces 900+ raw skeleton points to ~30-50 waypoints while preserving route shape.

## Tunable Parameters

| Parameter | Default | What it does |
|---|---|---|
| Darkness threshold | auto (5th percentile) | How dark a pixel must be. Lower = stricter. Leave blank for auto. |
| Bridge gaps | 11 | Morphological close kernel. Connects dotted lines. Higher bridges wider gaps but may merge nearby features. Set to 1 to disable. |
| Min size | 50 | Ignore blobs smaller than this (pixels). Raise to skip text labels. |
| Trim stubs | 10 | Branch pruning passes. Higher = cleaner routes but may clip real turns. |
| Smoothing | 2.0 | Douglas-Peucker epsilon. Higher = fewer points, straighter. Lower = more points, follows wiggles. |

## Test Results

With generous defaults (5th percentile threshold, close=11):

| Map | Candidates | Substantial (>50px path) | Notes |
|---|---|---|---|
| page_194 (overview) | 15 | 7 | Dotted routes now detected |
| page_195 (detailed) | 30 | 7 | Main route + text fragments |
| page_200 (detailed) | 25 | 9 | Two route lines visible |
| page_204 (detailed) | 11 | 1 | Clean single route |
| page_210 (detailed) | 26 | 4 | Two routes (Hike 21 + 22) |

## Dependencies

- OpenCV 4.13.0 (`cv2`) — already installed
- numpy — already installed
- No scipy, no scikit-image needed

## UX Design

- "Detect Routes" button in trace section
- Each detected candidate rendered as a colored polyline overlay (orange, magenta, cyan, lime...)
- Per-candidate row: color swatch, point count, path length, Accept / Reject buttons
- Accept → converts to waypoints in the trace list
- Reject → removes the overlay
- Collapsible "Adjust detection" panel with parameter descriptions
- Philosophy: detect aggressively, let the user curate

## Implementation Checklist

- [ ] 1. Image processing module with standalone pure functions: `auto_threshold()`, `remove_borders()`, `morphological_thin()`, `prune_branches()`, `find_longest_path()`, `extract_routes()`

- [ ] 2. API endpoint `POST /api/autotrace` — takes image name + optional param overrides, returns candidate list as JSON with pixel coordinates

- [ ] 3. Frontend: auto-trace state (candidates array), colored polyline overlay drawing on canvas

- [ ] 4. Frontend: "Detect Routes" button, fetch + render candidates

- [ ] 5. Frontend: per-candidate accept/reject UI

- [ ] 6. Frontend: collapsible parameter controls with human-readable descriptions

## Verification

1. Load page_194 (overview with dotted lines), detect → should find 5+ substantial candidates including the main routes
2. Load page_195 (detailed topo), detect → main route should be the longest candidate
3. Accept a route, set GCPs, compute transform, export CSV → valid lat/lon
4. Adjust parameters (raise threshold, increase bridge gaps) → more/different candidates appear
