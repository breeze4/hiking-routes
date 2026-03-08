# Arrow Detection + Text Labeling

**Status: SHELVED** — Interesting idea but not useful enough to justify the complexity. Arrow shapes are noisy at this scale and OCR on small GIF text is unreliable. Manual labeling is faster for ~12 arrows per map.

## Context

Scanned topo maps have arrows pointing to locations of interest (passes, exits, landmarks) with short text labels nearby. page_216 has ~12 such arrows. Goal: detect arrows, find their tip positions, OCR the nearby text, return labeled waypoints.

## Key Insight

Arrow detection needs `close_kernel=1` (no morphological close). The route pipeline uses close_kernel=11 to bridge dotted lines, but that merges arrows with nearby text. Arrows are already solid shapes — no closing needed.

## Algorithm

### Arrow shape detection
From connected components on the un-closed binary mask:
1. **Size filter**: area 40-4000 px² (excludes noise and routes)
2. **Elongation filter**: bounding box aspect > 1.3
3. **Skeleton branch test**: Skeletonize, find branch points (pixels with 3+ neighbors). Arrows have 1-3 branch points (Y-shape at arrowhead). Text characters like K, Y, T also branch, so:
4. **Arm length ratio**: From the branch point, trace 3 arms. Two short barbs + one long shaft. If longest arm < 2x shortest, reject (probably text).

### Tip and direction
- Tip = branch point position (where barbs converge)
- Tail = far end of the longest arm (shaft end)
- Direction = `atan2(tip_y - tail_y, tip_x - tail_x)` in degrees

### Text OCR
- Search region: 120x80px rectangle centered ~40px beyond the tail, away from tip
- Crop grayscale, upscale 3x with INTER_CUBIC, binarize
- `pytesseract.image_to_string(crop, config='--psm 7')` (single line mode)
- Whitelist lowercase + space to reduce noise

## Files to modify

- `georef-app/processing/autotrace.py` — refactor `_preprocess()` helper, add arrow detection helpers + `detect_arrows()`
- `georef-app/tests/test_autotrace.py` — add arrow visualization to HTML report
- `georef-app/models.py` — add `ArrowDetectRequest`
- `georef-app/api/autotrace.py` — add `POST /api/detect-arrows`

## Checklist

- [ ] 1. Refactor shared preprocessing into `_preprocess()` helper. `extract_routes` calls it. No behavior change.
- [ ] 2. Add `_find_branch_points(skeleton)` — returns list of (y,x) with 3+ neighbors
- [ ] 3. Add `_classify_arrow(mask)` — skeletonize, check branch points, measure arm lengths. Returns tip/tail coords or None.
- [ ] 4. Add `_ocr_arrow_label(gray, tail_yx, direction_deg, search_radius)` — crop, upscale, pytesseract
- [ ] 5. Add `detect_arrows()` public function — preprocess with close_kernel=1, filter components, classify, OCR
- [ ] 6. Run on page_216, verify ~12 arrows detected with correct labels
- [ ] 7. Add `ArrowDetectRequest` model + API endpoint
- [ ] 8. Update test report: draw arrow tips, direction lines, labels on overlay; add arrow legend table
- [ ] 9. Run full report, verify arrow visualization

## Verification

- page_216: should detect ~12 arrows with labels (pass, enter, exit, arch, lsg, lph x4, sand dune, N)
- Check that route detection still works unchanged (same results as before refactor)
