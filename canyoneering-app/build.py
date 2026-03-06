#!/usr/bin/env python3
"""Build script for Canyoneering 3 multi-page site.

Discovers markdown files in content/, parses YAML front matter,
converts to HTML, generates nav, and assembles pages.
Outputs to html/canyoneering-3/.
"""

import re
import shutil
import yaml
import markdown
from pathlib import Path

APP_DIR = Path(__file__).parent
ROOT = APP_DIR.parent
BASE = ROOT / "html" / "canyoneering-3"
CONTENT_DIR = APP_DIR / "content"
TEMPLATE = APP_DIR / "template.html"

# Ordered list of content subdirectories
DIR_ORDER = [
    "front-matter",
    "region-i",
    "region-ii",
    "region-iii",
    "region-iv",
    "back-matter",
]

# h3 headings matching these patterns are metadata, not nav-worthy sections.
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

ROAD_SECTION_PATTERNS = [
    r"Road Section",
    r"End of side",
    r"Side road",
    r"Side track",
]
ROAD_SECTION_RE = re.compile("|".join(ROAD_SECTION_PATTERNS), re.IGNORECASE)

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
    return re.sub(r"<[^>]+>", "", html).strip()


def discover_pages():
    """Discover .md files from content directories, return list of page dicts."""
    pages = []
    md_ext = markdown.Markdown(extensions=["attr_list"])

    for subdir_name in DIR_ORDER:
        subdir = CONTENT_DIR / subdir_name
        if not subdir.exists():
            continue
        for md_path in sorted(subdir.glob("*.md")):
            text = md_path.read_text()
            # Parse YAML front matter
            if text.startswith("---"):
                _, fm_str, body = text.split("---", 2)
                meta = yaml.safe_load(fm_str)
                body = body.strip()
            else:
                meta = {}
                body = text

            # Convert markdown to HTML
            md_ext.reset()
            html_content = md_ext.convert(body)

            pages.append({
                "slug": meta.get("slug", md_path.stem),
                "title": meta.get("title", md_path.stem),
                "type": meta.get("type", "front-matter"),
                "region": meta.get("region"),
                "content_id": meta.get("content_id"),
                "number": meta.get("number"),
                "html": html_content,
                "file": str(md_path.relative_to(CONTENT_DIR)),
            })

    return pages


def generate_title_heading(page):
    """Generate the title heading HTML from front matter."""
    ptype = page["type"]
    title = page["title"]
    slug = page["slug"]

    if ptype == "hike":
        # Extract display title (without number prefix like "1. ")
        display_title = re.sub(r"^\d+\.\s*", "", title)
        number = page.get("number", "")
        return f'<h3 id="{slug}"><em>{display_title}</em><em>Hike #{number}</em></h3>\n'
    elif ptype == "region":
        content_id = page.get("content_id", slug)
        return f'<h2 id="{content_id}">{title}</h2>\n'
    elif ptype == "front-matter":
        return f'<h2 id="{slug}">{title}</h2>\n'
    elif ptype == "back-matter":
        return f'<h2 id="{slug}">{title}</h2>\n'
    return ""


def extract_h3_headings(html, slug=None):
    """Extract (id, text) pairs from h3 tags, filtering blocklisted ones."""
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
    if ROAD_SECTION_RE.search(text):
        return "road-section"
    if NARRATIVE_RE.search(text):
        return "narrative"
    return None


def generate_nav_html(pages, page_headings):
    lines = []
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
            lines.append(f'    <div class="region-label"><a href="{href}">{title}</a></div>')
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
    pages = discover_pages()
    template = TEMPLATE.read_text()

    # Build full content (title heading + rendered markdown) for each page
    page_contents = {}
    page_headings = {}
    for page in pages:
        slug = page["slug"]
        title_heading = generate_title_heading(page)
        full_content = title_heading + page["html"]
        page_contents[slug] = full_content
        page_headings[slug] = extract_h3_headings(full_content, slug)

    # Generate nav HTML (shared across all pages)
    nav_html = generate_nav_html(pages, page_headings)

    # Build each page
    for page in pages:
        slug = page["slug"]
        title = page["title"]
        content = page_contents[slug]

        output = template.replace("{{TITLE}}", title)
        output = output.replace("{{NAV}}", nav_html)
        output = output.replace("{{CONTENT}}", content)

        out_path = BASE / f"{slug}.html"
        out_path.write_text(output)
        print(f"  built {slug}.html")

    # Build index.html
    index_content = generate_index_content(pages)
    index_output = template.replace("{{TITLE}}", "Table of Contents")
    index_output = index_output.replace("{{NAV}}", nav_html)
    index_output = index_output.replace("{{CONTENT}}", index_content)
    (BASE / "index.html").write_text(index_output)
    print(f"  built index.html")

    # Copy shared assets
    for asset in ("style.css", "nav.js"):
        shutil.copy2(APP_DIR / asset, BASE / asset)
        print(f"  copied {asset}")

    print(f"\nDone. {len(pages) + 1} pages built.")


if __name__ == "__main__":
    build()
