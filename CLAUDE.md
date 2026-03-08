# Hiking Route Planner

## Project Overview

A personal, static site for planning and viewing hiking trips. Each trip is a self-contained HTML page with embedded maps (CalTopo iframes), photos, and route descriptions. No backend, no multi-user features, no management UI — just static HTML files you open in a browser.

The site supports multiple trips via lightweight navigation chrome. Each trip page stands alone but is linked from a shared nav.

The first trip (Muddy Creek) was bootstrapped from Steve Allen's "Canyoneering 2: Technical Loop Hikes in Southern Utah" via the `extract.py` tool. Future trips may come from other sources or be written from scratch.

## Project Structure

```
html/
  index.html                  ← trip list page (links to each trip)
  trips.js                    ← shared nav bar (injected into each trip page)
  muddy-creek/
    index.html                ← Muddy Creek trip page
    images/                   ← extracted images (book maps, photos)
    text/                     ← per-page extracted text from EPUB (reference)
    text.txt                  ← combined extracted text (reference)
  stevens-canyon/
    index.html                ← Stevens Canyon & Baker Route (stub)
  canyoneering-3/             ← Canyoneering 3 book — BUILT OUTPUT
    index.html                ← BUILT: table of contents
    *.html                    ← BUILT: individual pages
    style.css                 ← BUILT: copied from canyoneering-app/
    nav.js                    ← BUILT: copied from canyoneering-app/
    images/                   ← extracted images
canyoneering-app/             ← Canyoneering 3 build system — SOURCE
  build.py                    ← builds pages from markdown content
  template.html               ← shared page shell
  style.css                   ← shared CSS
  nav.js                      ← runtime nav behavior
  content/                    ← markdown source files with YAML front matter
    front-matter/             ← 12 intro/reference chapters
    region-i/                 ← Box-Death Hollow Wilderness (hikes 1-3)
    region-ii/                ← Highway 12 Area (hikes 5-9)
    region-iii/               ← Hole-In-The-Rock (hikes 10-28)
    region-iv/                ← Burr Trail (hikes 30-37)
    back-matter/              ← bibliography, acknowledgments
georef-app/                   ← Georeferencing tool — SOURCE
  server.py                   ← FastAPI entry point + static file mount
  config.py                   ← Settings (image dir, data dir, port)
  models.py                   ← Pydantic API models
  api/                        ← API routers (images, transform, export, persistence, autotrace)
  processing/                 ← Image processing (autotrace OpenCV pipeline)
  frontend/                   ← SPA frontend (vanilla ES modules, no build step)
    index.html                ← Shell HTML
    css/style.css             ← Styles
    js/                       ← app.js, api.js, canvas.js, gcp.js, trace.js, autotrace.js, persistence.js
caltopo-extension/            ← Chrome extension for batch-adding CalTopo markers
  manifest.json               ← Manifest V3 config
  popup.html                  ← Extension popup UI
  popup.js                    ← Map ID detection, CSV parsing, API calls
input/                        ← private data sources (CSV, text files). Gitignored.
extract.py                    ← PDF/EPUB text extractor. Done. Don't modify unless asked.
output/                       ← raw extractor output. Don't edit — regenerate via extract.py.
```

## Architecture

Static HTML files. No framework, no JS dependencies beyond what's inline in the HTML. CalTopo maps are embedded via iframes.

**Canyoneering 3 build:** `canyoneering-app/build.py` discovers markdown files in `canyoneering-app/content/`, parses YAML front matter, converts markdown to HTML via Python-Markdown, and assembles pages using `template.html`. No manifest file — page ordering is derived from directory structure and filename prefixes. Run `python3 canyoneering-app/build.py` from the repo root after editing any source file. Built HTML files are committed to git (opened directly in a browser, no server needed). Dependencies: `pyyaml`, `markdown` (both in system packages).

**Formatting:** HTML files are formatted with `js-beautify` (2-space indent), which matches VS Code's built-in HTML formatter. VS Code has `editor.formatOnSave: true` enabled.

### Multi-Trip Navigation

`html/trips.js` injects a fixed nav bar into each trip page. Trip pages reference it via `<script src="../trips.js"></script>`. The script detects the current trip by directory name in the URL path.

`html/index.html` is a simple list of links to each trip — no nav bar, no JS.

### CalTopo Map Embeds

CalTopo maps are embedded as iframes using the pattern:
```html
<iframe src="https://caltopo.com/m/{MAP_ID}" allowfullscreen></iframe>
```

Maps can be displayed side-by-side with printed book maps using a `.map-pair` flex container that breaks out wider than the text column.

### CalTopo Extension

A Chrome extension (Manifest V3) in `caltopo-extension/` for batch-adding markers to CalTopo maps from CSV input.

**Files:** `manifest.json`, `popup.html`, `popup.js` — no content script, no build step.

**How it works:**
- Popup reads the active tab URL to extract the CalTopo map ID (`caltopo.com/m/{id}` or `caltopo.com/map/{id}`)
- User pastes CSV in `name,lat,lon` format (one marker per line)
- Each marker is POSTed as a GeoJSON Feature to `POST /api/v1/map/{mapId}/Marker/` with `Content-Type: application/x-www-form-urlencoded` and body `json={encoded GeoJSON}`
- `host_permissions` on `caltopo.com` lets the browser include session cookies — no API key needed
- GeoJSON coordinates use `[longitude, latitude]` order (swapped from the CSV input)
- Results show per-marker success/failure in the popup

### Trip Page Structure

Each trip page is organized by trail sections with `<h3>` headings. Sections have descriptive text and may include embedded photos/maps.

For the Muddy Creek trip, sections are:
- Road Section, Down Muddy Creek, Through The Chute, To Mud Canyon, Up Mud Canyon, Across Keesle Country, To Cistern Canyon, Down Cistern Canyon, To Muddy Creek, To Hidden Splendor, To the exit canyon, To Chimney Canyon, Up Chimney Canyon, Exploring the South Fork, Exploring the North Fork, To the Pasture Track, Along the Pasture Track

## Current State

- Muddy Creek trip: EPUB text extracted and formatted as semantic HTML
- First CalTopo map (`https://caltopo.com/m/HET5V0R`) embedded alongside the printed overview map
- Multi-trip nav implemented via `trips.js`
- Trip pages reorganized into per-trip directories
- Stevens Canyon stub page created
- CalTopo extension: implemented — manifest, popup UI, CSV parsing, and marker API calls
- Canyoneering 3: full book as 48 markdown files, built to HTML via canyoneering-app/build.py
