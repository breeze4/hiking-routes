# Muddy Creek Interactive Hiking Planner

## Project Overview

This started as a PDF/EPUB text extractor but has evolved into an interactive hiking planner. The extractor (`extract.py`) is done — all future work is on the HTML output directly.

The source material is from Steve Allen's "Canyoneering 2: Technical Loop Hikes in Southern Utah", specifically the Muddy Creek section covering a multi-day canyon loop in the San Rafael Swell.

## Working Files

- **`html/index.html`** — The live working file. Edit this directly.
- **`html/images/`** — Extracted images (book maps, photos) referenced as base64 data URIs in the HTML.
- **`html/text/`** — Per-page extracted text (reference only).
- **`extract.py`** — The extractor. Done. Don't modify unless asked.
- **`output/`** — Raw extractor output. Don't edit — regenerate via extract.py if needed.

## Architecture

Single self-contained HTML file. All images are embedded as base64 data URIs. CalTopo maps are embedded via iframes. No build step, no framework, no JS dependencies — just open `html/index.html` in a browser.

### CalTopo Map Embeds

CalTopo maps are embedded as iframes using the pattern:
```html
<iframe src="https://caltopo.com/m/{MAP_ID}" allowfullscreen></iframe>
```

The first map is displayed side-by-side with the printed book map using a `.map-pair` flex container that breaks out wider than the 680px text column. More CalTopo embeds will be added for different trail sections.

### Content Structure

The report is organized by trail sections with `<h3>` headings:
- Road Section, Down Muddy Creek, Through The Chute, To Mud Canyon, Up Mud Canyon, Across Keesle Country, To Cistern Canyon, Down Cistern Canyon, To Muddy Creek, To Hidden Splendor, To the exit canyon, To Chimney Canyon, Up Chimney Canyon, Exploring the South Fork, Exploring the North Fork, To the Pasture Track, Along the Pasture Track

Each section has descriptive text, and some have embedded photos/maps from the book.

## Current State

- EPUB text extracted and formatted as semantic HTML
- First CalTopo map (`https://caltopo.com/m/HET5V0R`) embedded at top alongside the printed overview map
- More CalTopo section maps to be added by the user
