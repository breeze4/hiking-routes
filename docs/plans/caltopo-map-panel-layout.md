# CalTopo Map Panel Layout for Canyoneering App

## Context

The canyoneering-app pages are used for route planning. The user wants to read route descriptions while simultaneously editing a CalTopo map. This requires a split-pane layout: scrollable text on the left at a fixed width, and a persistent CalTopo map iframe on the right that fills remaining space and stays fixed while text scrolls.

This is a desktop editing workflow — on narrow screens, the map panel should be hidden and the normal layout shown.

## Files to Modify

1. **`canyoneering-app/style.css`** — Add `body.has-map` layout styles
2. **`canyoneering-app/template.html`** — Add `{{BODY_CLASS}}` and `{{MAP_PANEL}}` placeholders
3. **`canyoneering-app/build.py`** — Read `map` front matter field, inject class/panel

## Implementation

### Step 1: Update template.html

Add a body class placeholder and a map panel slot:

```
<body{{BODY_CLASS}}>
  <nav>...</nav>
  <script src="nav.js"></script>
  <main class="content">
    {{CONTENT}}
  </main>
  {{MAP_PANEL}}
  <script src="../trips.js"></script>
</body>
```

Always wrap content in `<main class="content">` (for both map and non-map pages). The `{{BODY_CLASS}}` resolves to ` class="has-map"` or empty. `{{MAP_PANEL}}` resolves to the iframe div or empty.

### Step 2: Update build.py

- Read `map` front matter field (CalTopo map ID string, e.g. `map: HET5V0R`)
- Store it in the page dict
- When building each page:
  - If `map` is set: `BODY_CLASS` = ` class="has-map"`, `MAP_PANEL` = `<div class="map-panel"><iframe src="https://caltopo.com/m/{map_id}" allowfullscreen></iframe></div>`
  - If not: both placeholders resolve to empty string

### Step 3: Add CSS for map layout

Key styles on `body.has-map`:
- `max-width: none; margin: 0; padding: 0;` — override default centered body
- `display: flex; height: 100vh; overflow: hidden;` — fill viewport, no body scroll

`body.has-map main.content`:
- `width: 680px; flex-shrink: 0;` — fixed text width
- `overflow-y: auto; padding: 2rem 1rem 4rem;` — scrollable text area

`body.has-map .map-panel`:
- `flex: 1; min-width: 300px;` — fill remaining space

`body.has-map .map-panel iframe`:
- `width: 100%; height: 100%; border: none;`

Desktop media query (>=1250px):
- `body.has-map { margin-left: 250px; }` — account for fixed nav sidebar

Mobile/narrow (<=1249px):
- Hide `.map-panel`, remove flex/overflow constraints from body.has-map so normal mobile layout applies
- The existing mobile nav (top bar) works as-is since content is in `<main>`

### Step 4: Verify non-map pages unchanged

The `<main class="content">` wrapper is new but transparent — body still has `max-width: 680px` and `margin: 0 auto`, so `<main>` just flows normally inside it. No visual change for non-map pages.

### Step 5: Rebuild and verify

Run `python3 canyoneering-app/build.py` and open a page in a browser to verify.

## Verification

1. `python3 canyoneering-app/build.py` succeeds
2. Open a non-map page — layout unchanged
3. Add `map: HET5V0R` to a test page's front matter, rebuild, verify split layout
4. Confirm text scrolls independently, map stays fixed
5. Confirm nav sidebar still works on desktop
6. Confirm mobile layout degrades gracefully (no map, normal scroll)
