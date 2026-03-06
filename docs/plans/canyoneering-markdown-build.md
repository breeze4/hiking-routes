# Replace Canyoneering-3 HTML Build with Markdown-Based Build

## Context

The current canyoneering-3 system takes HTML fragment source files and assembles them into worse-organized HTML output, duplicating the full nav structure into every page. The source files are HTML fragments that aren't pleasant to read or edit. We want human-readable markdown source files with YAML front matter, converted to the same HTML output via a Python build step.

## Architecture

New `canyoneering-app/` directory at repo root containing:
- `build.py` — discovers markdown files, converts to HTML, assembles pages
- `template.html`, `style.css`, `nav.js` — copied from current `src/` (unchanged)
- `content/` — markdown files organized by section

No `pages.json` manifest. The build script discovers files from the filesystem and reads front matter.

Output still goes to `html/canyoneering-3/` (same as today). Images stay in `html/canyoneering-3/images/` (referenced as `images/...` in markdown).

**Dependencies:** `pyyaml`, `markdown` (Python-Markdown with `attr_list` extension for heading IDs)

### Content directory structure

```
content/
  front-matter/
    01-introduction.md
    02-wilderness.md
    03-protecting-the-environment.md
    04-the-geology-of-the-escalante-region.md
    05-the-strata.md
    06-man-in-the-escalante-the-prehistoric-period.md
    07-man-in-the-escalante-the-historic-period.md
    08-equipment.md
    09-the-art-of-travel.md
    10-technical-canyoneering.md
    11-access.md
    12-how-to-use-this-guide.md
  region-i/
    00-region-i.md
    01-death-hollow.md
    02-sand-creek.md
    03-boulder-mail-trail.md
  region-ii/
    00-region-ii.md
    05-middle-boulder-creek.md
    06-upper-boulder-creek-and-dry-hollow.md
    07-phipps-wash.md
    08-big-horn-canyon.md
    09-the-escalante-river-and-the-sand-slides.md
  region-iii/
    00-region-iii.md
    10-red-breaks-canyon.md
    ...15 hike files
  region-iv/
    00-region-iv.md
    30-deer-creek.md
    ...8 hike files
  back-matter/
    01-bibliography.md
    02-acknowledgments.md
```

### Markdown file format

```yaml
---
title: Death Hollow
slug: death-hollow
type: hike
region: I
number: 1
---
```

Front matter fields: `title`, `slug`, `type` (front-matter/region/hike/back-matter). Hikes add `region` and `number`. Regions add `region` and `content_id`.

Body content is markdown. Most content converts cleanly:
- `<p>` → plain paragraphs
- `<h3 id="...">` → `### Heading {#id}`
- `<em>` → `*text*`
- `<blockquote>` → `> text`

Three patterns stay as inline HTML (Python-Markdown passes these through):
- `<figure>` blocks (images with captions)
- `<p class="small">` (asides/digressions)
- `<br>` tags within blockquotes

The em-wrapped title h3 (`<h3><em>Death Hollow</em><em>Hike #1</em></h3>`) is NOT in the markdown — the build script generates it from front matter.

### Build script behavior

Same as current `build.py` but with markdown input:
1. Discover `.md` files from `content/` subdirectories (hardcoded directory order)
2. Parse YAML front matter + markdown body from each file
3. Convert markdown → HTML via `markdown.markdown()` with `attr_list` extension
4. Prepend generated title heading (from front matter) to rendered HTML
5. Extract h3 headings from rendered HTML for nav (same regex/logic as current build)
6. Generate nav HTML, substitute template, write output files
7. Build index.html table of contents
8. Copy style.css and nav.js to output directory

## Tasks

### Phase 1: Scaffold

- [x] **1.1** Create `canyoneering-app/` with `content/` subdirectories, copy `template.html`, `style.css`, `nav.js` from `html/canyoneering-3/src/`
- [x] **1.2** Add `requirements.txt` with `pyyaml` and `markdown`
- [x] **1.3** Write minimal `build.py` skeleton: discovers `.md` files, reads front matter, prints sorted page list. Verify it runs (empty output since no content yet).

### Phase 2: HTML-to-Markdown conversion

- [x] **2.1** Write `canyoneering-app/convert.py`: reads current `pages.json` + HTML fragments, generates YAML front matter from manifest entries, converts HTML content to markdown (paragraphs, headings with `{#id}`, emphasis, blockquotes; leaves figures/p.small/br as HTML), strips the title h3 from hike pages, writes `.md` files to `content/` directories.
- [x] **2.2** Run conversion. Verify all 48 `.md` files created with correct front matter and content.
- [x] **2.3** Spot-check a few converted files for correctness (death-hollow, region-i, introduction, bibliography).

### Phase 3: Build script

- [x] **3.1** Add markdown→HTML rendering: parse front matter with pyyaml, render body with `markdown` library (`attr_list` extension).
- [x] **3.2** Add title heading injection from front matter (hike: em-wrapped h3 with title + number; region: h2 with content_id; front-matter: h2 with slug).
- [x] **3.3** Port heading extraction + nav generation from old `build.py` (functions transfer nearly verbatim — they operate on rendered HTML).
- [x] **3.4** Port template substitution + page output. Port index.html generation. Copy assets.
- [x] **3.5** Run build, diff output against current `html/canyoneering-3/*.html`. Fix differences until output matches.

### Phase 4: Cutover

- [x] **4.1** Visual verification: open front-matter, region, hike (with figures/images/small text), and back-matter pages in browser. Check nav on desktop and mobile.
- [x] **4.2** Remove old `html/canyoneering-3/src/` directory and old `build.py` at repo root.
- [x] **4.3** Remove `convert.py` (one-shot tool, no longer needed).
- [x] **4.4** Update `CLAUDE.md`: project structure, build instructions, source file locations.

## Risks

- **Heading ID mismatch**: Python-Markdown auto-generates IDs differently than the current manual IDs. Mitigation: use `{#id}` syntax in markdown (via `attr_list` extension) to set explicit IDs. The conversion script must emit these.
- **Raw HTML block handling**: `<figure>` and `<p class="small">` blocks must be separated by blank lines or Python-Markdown wraps them in `<p>` tags. Conversion script must ensure this.
- **Sort order**: Filename-based sort must match current `pages.json` order. Numeric prefixes handle this.

## Verification

1. Run `python3 canyoneering-app/build.py`
2. Diff all output files in `html/canyoneering-3/` against pre-migration versions
3. Open pages in browser and verify rendering + nav behavior
4. Check that `html/canyoneering-3/images/` references still work (paths unchanged)

## Key files

- Current build: `/home/breeze/dev/hiking-routes/build.py`
- Current manifest: `/home/breeze/dev/hiking-routes/html/canyoneering-3/src/pages.json`
- Current template: `/home/breeze/dev/hiking-routes/html/canyoneering-3/src/template.html`
- Sample hike (complex): `/home/breeze/dev/hiking-routes/html/canyoneering-3/src/pages/region-i/01-death-hollow.html`
- Output directory: `/home/breeze/dev/hiking-routes/html/canyoneering-3/`
