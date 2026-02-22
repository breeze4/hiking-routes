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
caltopo-extension/            ← Chrome extension for CalTopo (in progress, being specced)
extract.py                    ← PDF/EPUB text extractor. Done. Don't modify unless asked.
output/                       ← raw extractor output. Don't edit — regenerate via extract.py.
```

## Architecture

Static HTML files. No build step, no framework, no JS dependencies beyond what's inline in the HTML. CalTopo maps are embedded via iframes.

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

A Chrome extension (in `caltopo-extension/`) for adding waypoints and markers to CalTopo maps more efficiently. Currently being specced out — no implementation yet.

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
- CalTopo extension: being specced, directory exists but no code yet
