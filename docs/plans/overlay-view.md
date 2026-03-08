# Overlay View: Visual Image Placement

## Context

The overlay view currently only shows images that have pre-computed affine transforms from the GCP workflow. The user wants to skip GCPs entirely — instead, show all map images, let them drag/scale each one onto position on the Leaflet topo map, and save the placement.

## Approach

Replace read-only overlay display with interactive placement. All images appear in the sidebar. "Add" places an image on the map with 3 draggable handles (SW corner, NE corner, center). Drag corners to resize, drag center to move. Save computes affine coefficients from the axis-aligned bounds and persists to the same JSON format.

**Handle implementation:** 3 `L.marker` instances per image using `L.divIcon` (small colored squares). Corner handles resize, center handle moves. All use Leaflet's built-in `marker.dragging.enable()`. No external plugins.

**Data compatibility:** Visual placement produces `coeffs_lon = [(east-west)/w, 0, west]` and `coeffs_lat = [0, (south-north)/h, north]`. Also stores `bounds: [[south,west],[north,east]]` for reloading handle positions. Existing GCP-derived data still works.

## Files

**Modified:**
- `georef-app/models.py` — add optional `bounds` field to `SaveRequest`
- `georef-app/api/persistence.py` — include `bounds` in saved JSON
- `georef-app/api/overlay.py` — return ALL images with placement status, not just georeferenced ones
- `georef-app/frontend/index.html` — restructure overlay sidebar for image list + placement controls
- `georef-app/frontend/css/style.css` — handle marker styles, image list styles
- `georef-app/frontend/js/overlay-app.js` — major rewrite: image list, add/remove, handles, save
- `georef-app/frontend/js/api.js` — add `savePlacement()` wrapper

## Checklist

- [ ] **1. Backend: Add `bounds` to save model + expand overlays endpoint**
  - `models.py`: add `bounds: list[list[float]] | None = None` to `SaveRequest`
  - `persistence.py`: include `bounds` in saved JSON when present
  - `overlay.py`: return all images from `settings.image_dir`, each with `{image_name, label, placed, coeffs_lon, coeffs_lat, bounds, width, height}`. Placed images have transforms; unplaced have nulls.
  - `api.js`: add `savePlacement(imageName, coeffsLon, coeffsLat, bounds)` that POSTs to `/api/save`
  - **Verify:** curl `/api/overlays` returns all 9 images, 1 with `placed: true`

- [ ] **2. Update overlay sidebar HTML**
  - Replace "Map Layers" section with "Images" section containing `#image-list` div
  - Keep Points section unchanged
  - Each image rendered by JS: unplaced gets "Add" button, placed gets checkbox + slider + Save + Remove
  - **Verify:** Page loads, overlay sidebar shows new structure

- [ ] **3. Populate image list and show placed overlays**
  - Rewrite `loadOverlays()` to call expanded `/api/overlays`
  - Render all images in `#image-list`
  - Create `L.imageOverlay` for placed images, fit bounds
  - Unplaced images show "Add" button
  - **Verify:** All 9 images in sidebar, 1 on map

- [ ] **4. Implement "Add" — place image with handles**
  - Fetch image natural dimensions via `new Image()`
  - Compute initial bounds centered on viewport, aspect-ratio correct, ~1/4 viewport size
  - Create `L.imageOverlay` + 3 handle markers (SW, NE, center) with `L.divIcon` colored squares
  - Update sidebar item to show placed controls
  - CSS: `.handle-marker` (12x12 colored squares, cursor:move)
  - **Verify:** Click Add, image appears with 3 handles

- [ ] **5. Implement handle drag — resize and move**
  - SW/NE corner drag: update bounds, reposition opposite handle stays fixed, reposition center
  - Center drag: shift both corners by delta, reposition both corner handles
  - Call `imageOverlay.setBounds(newBounds)` on every drag event
  - **Verify:** Drag corners to resize, drag center to move

- [ ] **6. Implement Save and Remove**
  - Save: compute `coeffs_lon`/`coeffs_lat` from bounds + image dimensions, call `savePlacement()`, store bounds too
  - Remove: remove overlay + handles from map, revert sidebar to "Add" button
  - On reload, placed images with `bounds` get editable handles (not just static overlays)
  - **Verify:** Save placement, reload page, image loads in saved position with draggable handles

- [ ] **7. Update SPEC.md**

## Verification

1. Start server: `python3 georef-app/server.py`
2. Click "Overlay" tab — all 9 images in sidebar, 1 pre-placed on map
3. Click "Add" on an unplaced image — appears with handles
4. Drag corners to resize, drag center to move — aligns with topo
5. Click "Save" — reloads correctly after page refresh
6. Place points on top, export CSV
