# Hiking Route Planner

## Project Overview

A personal, static site for planning and viewing hiking trips. Each trip is a self-contained HTML page with embedded maps (CalTopo iframes), photos, and route descriptions. No backend, no multi-user features, no management UI — just static HTML files you open in a browser.

The site supports multiple trips via lightweight navigation chrome. Each trip page stands alone but is linked from a shared nav.

The first trip (Muddy Creek) was bootstrapped from Steve Allen's "Canyoneering 2: Technical Loop Hikes in Southern Utah" via the `extract.py` tool. Future trips may come from other sources or be written from scratch.

## Working Files

- **`html/`** — All trip pages live here. Each trip is its own HTML file.
  - **`html/index.html`** — The Muddy Creek trip (first and currently only trip page).
  - **`html/images/`** — Extracted images (book maps, photos) referenced as base64 data URIs.
  - **`html/text/`** — Per-page extracted text from the EPUB (reference only).
- **`extract.py`** — PDF/EPUB text extractor. Done. Don't modify unless asked.
- **`output/`** — Raw extractor output. Don't edit — regenerate via extract.py if needed.

## Architecture

Static HTML files. No build step, no framework, no JS dependencies beyond what's inline in the HTML. Images are embedded as base64 data URIs. CalTopo maps are embedded via iframes.

### Multi-Trip Navigation

Lightweight nav chrome shared across trip pages. Keep it minimal — a simple way to switch between trips, not a full app shell.

### CalTopo Map Embeds

CalTopo maps are embedded as iframes using the pattern:
```html
<iframe src="https://caltopo.com/m/{MAP_ID}" allowfullscreen></iframe>
```

Maps can be displayed side-by-side with printed book maps using a `.map-pair` flex container that breaks out wider than the text column.

### Trip Page Structure

Each trip page is organized by trail sections with `<h3>` headings. Sections have descriptive text and may include embedded photos/maps.

For the Muddy Creek trip, sections are:
- Road Section, Down Muddy Creek, Through The Chute, To Mud Canyon, Up Mud Canyon, Across Keesle Country, To Cistern Canyon, Down Cistern Canyon, To Muddy Creek, To Hidden Splendor, To the exit canyon, To Chimney Canyon, Up Chimney Canyon, Exploring the South Fork, Exploring the North Fork, To the Pasture Track, Along the Pasture Track

## Current State

- Muddy Creek trip: EPUB text extracted and formatted as semantic HTML
- First CalTopo map (`https://caltopo.com/m/HET5V0R`) embedded alongside the printed overview map
- Multi-trip nav not yet implemented
