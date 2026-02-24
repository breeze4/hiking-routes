#!/usr/bin/env python3
"""Build script for Canyoneering 3 multi-page site.

Reads pages.json manifest, page fragments from pages/, and template.html.
Generates nav HTML from manifest + extracted h3 headings.
Outputs assembled pages to html/canyoneering-3/.
"""

import json
import re
import shutil
from pathlib import Path

BASE = Path(__file__).parent / "html" / "canyoneering-3"
SRC = BASE / "src"
PAGES_DIR = SRC / "pages"
TEMPLATE = SRC / "template.html"
MANIFEST = SRC / "pages.json"

# h3 headings matching these patterns are metadata, not nav-worthy sections.
# All metadata headings end with a colon; section headings don't.
BLOCKLIST_PATTERNS = [
    r"^Season:",
    r"^Time:",
    r"^Elevation\s+range:",
    r"^Water:",
    r"^Maps?:",
    r"^Skill\s+level:",
    r"^Special\s+equipment:",
    r"^Note:",
    r"^Land\s+status:",
    r"^by\s",
]
BLOCKLIST_RE = re.compile("|".join(BLOCKLIST_PATTERNS), re.IGNORECASE)

# Patterns for classifying nav children
ROAD_SECTION_PATTERNS = [
    r"Road Section",
    r"End of side",
    r"Side road",
    r"Side track",
]
ROAD_SECTION_RE = re.compile("|".join(ROAD_SECTION_PATTERNS), re.IGNORECASE)

# Known narrative titles (region-level narrative sections)
NARRATIVE_PATTERNS = [
    r"^Part \d+:",
    r"^The Hole-In-The-Rock",
    r"^Hole-In-The-Rock",
    r"^Down the Escalante",
    r"^Up the Bowington",
    r"^Along the Bowington",
    r"^Back to the trailhead$",
    r"^Everett Ruess$",
    r"^The Overland Route",
]
NARRATIVE_RE = re.compile("|".join(NARRATIVE_PATTERNS), re.IGNORECASE)

H3_RE = re.compile(r'<h3\s+id="([^"]+)"[^>]*>(.*?)</h3>', re.DOTALL)


def strip_tags(html):
    """Remove HTML tags, returning plain text."""
    return re.sub(r"<[^>]+>", "", html).strip()


def extract_h3_headings(html, slug=None):
    """Extract (id, text) pairs from h3 tags, filtering blocklisted ones.

    Also filters out the page's own title h3 (where id matches slug).
    """
    headings = []
    for m in H3_RE.finditer(html):
        h3_id = m.group(1)
        if slug and h3_id == slug:
            continue
        text = strip_tags(m.group(2))
        if not BLOCKLIST_RE.search(text):
            headings.append((h3_id, text))
    return headings


def classify_heading(text):
    """Classify an h3 heading as road-section, narrative, or None (trail segment)."""
    if ROAD_SECTION_RE.search(text):
        return "road-section"
    if NARRATIVE_RE.search(text):
        return "narrative"
    return None


def generate_nav_html(pages, page_headings):
    """Generate the nav HTML for all pages."""
    lines = []
    current_region = None

    for page in pages:
        slug = page["slug"]
        title = page["title"]
        ptype = page["type"]
        href = f"{slug}.html"
        headings = page_headings.get(slug, [])

        if ptype == "front-matter":
            if headings:
                lines.append(f'    <details class="front-matter">')
                lines.append(f'      <summary><a href="{href}">{title}</a></summary>')
                for h3_id, h3_text in headings:
                    lines.append(f'      <a href="{href}#{h3_id}">{h3_text}</a>')
                lines.append(f'    </details>')
            else:
                lines.append(f'    <details class="front-matter">')
                lines.append(f'      <summary><a href="{href}">{title}</a></summary>')
                lines.append(f'    </details>')

        elif ptype == "region":
            current_region = page.get("region")
            lines.append(f'    <div class="region-label"><a href="{href}">{title}</a></div>')
            # Region headings (road sections, narratives) go directly under region label
            for h3_id, h3_text in headings:
                cls = classify_heading(h3_text)
                if cls == "road-section":
                    lines.append(f'      <a class="road-section" href="{href}#{h3_id}">{h3_text}</a>')
                elif cls == "narrative":
                    lines.append(f'      <a class="narrative" href="{href}#{h3_id}">{h3_text}</a>')
                else:
                    lines.append(f'      <a href="{href}#{h3_id}">{h3_text}</a>')

        elif ptype == "hike":
            lines.append(f'      <details class="hike-group">')
            lines.append(f'        <summary><a href="{href}">{title}</a></summary>')
            for h3_id, h3_text in headings:
                cls = classify_heading(h3_text)
                if cls == "road-section":
                    lines.append(f'      <a class="road-section" href="{href}#{h3_id}">{h3_text}</a>')
                else:
                    lines.append(f'        <a href="{href}#{h3_id}">{h3_text}</a>')
            lines.append(f'      </details>')

        elif ptype == "back-matter":
            lines.append(f'    <a class="back-matter" href="{href}">{title}</a>')

    return "\n".join(lines)


def generate_index_content(pages):
    """Generate the table of contents page content."""
    lines = ['<h1>Canyoneering 3</h1>']
    in_hikes = False

    for page in pages:
        slug = page["slug"]
        title = page["title"]
        ptype = page["type"]
        href = f"{slug}.html"

        if ptype == "front-matter":
            if in_hikes:
                lines.append('</ol>')
                in_hikes = False
            lines.append(f'<p class="toc-front"><a href="{href}">{title}</a></p>')
        elif ptype == "region":
            if in_hikes:
                lines.append('</ol>')
                in_hikes = False
            lines.append(f'<h2><a href="{href}">{title}</a></h2>')
        elif ptype == "hike":
            if not in_hikes:
                lines.append('<ol class="toc-hikes">')
                in_hikes = True
            lines.append(f'<li><a href="{href}">{title}</a></li>')
        elif ptype == "back-matter":
            if in_hikes:
                lines.append('</ol>')
                in_hikes = False
            lines.append(f'<p class="toc-back"><a href="{href}">{title}</a></p>')

    if in_hikes:
        lines.append('</ol>')

    return "\n".join(lines)


def build():
    pages = json.loads(MANIFEST.read_text())
    template = TEMPLATE.read_text()

    # Extract h3 headings from each page fragment
    page_headings = {}
    for page in pages:
        slug = page["slug"]
        frag_path = PAGES_DIR / f"{slug}.html"
        if frag_path.exists():
            content = frag_path.read_text()
            page_headings[slug] = extract_h3_headings(content, slug)
        else:
            page_headings[slug] = []
            print(f"  warning: missing fragment pages/{slug}.html")

    # Generate nav HTML once (shared across all pages)
    nav_html = generate_nav_html(pages, page_headings)

    # Build each page
    for page in pages:
        slug = page["slug"]
        title = page["title"]
        frag_path = PAGES_DIR / f"{slug}.html"

        if frag_path.exists():
            content = frag_path.read_text()
        else:
            content = f"<h1>{title}</h1>\n<p>(Content not yet available.)</p>"

        output = template.replace("{{TITLE}}", title)
        output = output.replace("{{NAV}}", nav_html)
        output = output.replace("{{CONTENT}}", content)

        out_path = BASE / f"{slug}.html"
        out_path.write_text(output)
        print(f"  built {slug}.html")

    # Build index.html (table of contents)
    index_content = generate_index_content(pages)
    index_output = template.replace("{{TITLE}}", "Table of Contents")
    index_output = index_output.replace("{{NAV}}", nav_html)
    index_output = index_output.replace("{{CONTENT}}", index_content)
    (BASE / "index.html").write_text(index_output)
    print(f"  built index.html")

    # Copy shared assets from src/ so relative paths in built pages work
    for asset in ("style.css", "nav.js"):
        shutil.copy2(SRC / asset, BASE / asset)
        print(f"  copied {asset}")

    print(f"\nDone. {len(pages) + 1} pages built.")


if __name__ == "__main__":
    build()
