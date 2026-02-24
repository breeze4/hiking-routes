#!/usr/bin/env python3
"""Transform the auto-generated Canyoneering 3 HTML into a navigable reference page.

Reads the base64-embedded HTML from output/, replaces images with external file
references, adds IDs to all headings, and generates a lightweight chapter/section nav.
"""

import base64
import hashlib
import re
from pathlib import Path

SRC = Path("output/Canyoneering 3/index.html")
DST = Path("html/canyoneering-3/index.html")
IMG_DIR = Path("html/canyoneering-3/images")

# Metadata fields to exclude from nav entirely
METADATA_FIELDS = {
    "Season:", "Time:", "Water:", "Elevation range:", "Elevation Range:",
    "Maps:", "Map:", "Skill level:", "Special equipment:", "Note:",
    "Land status:", "Land Status:",
}

HIKE_RE = re.compile(r"Hike\s*#(\d+)")
ROAD_SECTION_RE = re.compile(r"Road Section$|^End [Oo]f [Ss]ide|^Side [Rr]oad|^Side [Tt]rack|^End Of Side")

# Chapter h2s that contain numbered hikes (the four regions)
REGION_CHAPTERS = {"i", "ii", "iii", "iv"}


def build_image_hash_map():
    hmap = {}
    for f in sorted(IMG_DIR.iterdir()):
        data = f.read_bytes()
        h = hashlib.md5(data).hexdigest()
        hmap[h] = f.name
    return hmap


def extract_base64_data(data_uri):
    match = re.match(r"data:image/[^;]+;base64,(.+)", data_uri, re.DOTALL)
    if match:
        return base64.b64decode(match.group(1))
    return None


def slugify(text):
    text = re.sub(r"<[^>]+>", "", text)
    text = text.strip()
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug


def clean_heading_text(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s*Hike\s*#\d+\s*$", "", text).strip()
    return text


def classify_h3(raw_content, display):
    """Returns ('skip'|'hike'|'road'|'section', hike_num_or_None)"""
    if display in METADATA_FIELDS:
        return "skip", None
    if display.startswith("by ") and "Allen" in display:
        return "skip", None

    hike_match = HIKE_RE.search(raw_content)
    # Only classify as a hike if the heading IS the hike title,
    # not a road section that mentions a hike number
    if hike_match and not ROAD_SECTION_RE.search(display):
        return "hike", int(hike_match.group(1))

    if ROAD_SECTION_RE.search(display):
        return "road", None
    return "section", None


def clean_chapter_heading(content):
    cleaned = re.sub(r"\s*<br\s*/?>\s*(<br\s*/?>\s*)?", " ", content)
    cleaned = re.sub(r"^(I{1,3}V?|IV|VI{0,3})\s+", r"\1. ", cleaned)
    return cleaned


def is_region_chapter(slug):
    """Check if a chapter slug is one of the four region chapters (I-IV)."""
    prefix = slug.split("-")[0]
    return prefix in REGION_CHAPTERS


def main():
    html = SRC.read_text()
    img_hashes = build_image_hash_map()

    used_slugs = {}

    def unique_slug(slug):
        if slug not in used_slugs:
            used_slugs[slug] = 0
            return slug
        used_slugs[slug] += 1
        return f"{slug}-{used_slugs[slug]}"

    # 1. Replace base64 images with file references
    def replace_img(match):
        full_tag = match.group(0)
        data_uri = match.group(1)
        raw = extract_base64_data(data_uri)
        if raw:
            h = hashlib.md5(raw).hexdigest()
            if h in img_hashes:
                filename = img_hashes[h]
                return full_tag.replace(data_uri, f"images/{filename}")
        return full_tag

    html = re.sub(
        r'<img\s+src="(data:image/[^"]+)"',
        replace_img,
        html,
    )

    # 2. Fix chapter headings with <br><br> in them
    def fix_h2(match):
        content = match.group(1)
        if "<br" in content:
            content = clean_chapter_heading(content)
        return f"<h2>{content}</h2>"

    html = re.sub(r"<h2>(.*?)</h2>", fix_h2, html, flags=re.DOTALL)

    # 3. Add IDs to h2 and h3 headings, collect nav structure
    # nav_items: (tag, slug, display, kind, hike_num)
    nav_items = []

    def add_heading_id(match):
        tag = match.group(1)
        content = match.group(2)
        display = clean_heading_text(content)
        slug = unique_slug(slugify(display))

        if tag == "h2":
            kind, hike_num = "chapter", None
        else:
            kind, hike_num = classify_h3(content, display)

        nav_items.append((tag, slug, display, kind, hike_num))
        return f'<{tag} id="{slug}">{content}</{tag}>'

    html = re.sub(
        r"<(h[23])>(.*?)</\1>",
        add_heading_id,
        html,
        flags=re.DOTALL,
    )

    # 4. Build nav and inject
    nav_html = build_nav(nav_items)
    html = inject_styles_and_nav(html, nav_html)

    DST.write_text(html)
    print(f"Written to {DST}")
    counts = {}
    for _, _, _, kind, _ in nav_items:
        counts[kind] = counts.get(kind, 0) + 1
    hike_nums = sorted(n for _, _, _, k, n in nav_items if k == "hike" and n)
    print(f"  Headings: {len(nav_items)} total — {counts}")
    print(f"  Hikes: {hike_nums}")
    print(f"  File size: {DST.stat().st_size / 1024:.0f} KB")


def build_nav(nav_items):
    """Build nav with hikes as the primary collapsible items."""
    lines = []
    lines.append('<nav class="outline">')
    lines.append('  <div class="outline-toggle">')
    lines.append('    <span class="outline-current">Contents</span>')
    lines.append('    <span class="outline-chevron">&#9660;</span>')
    lines.append("  </div>")
    lines.append('  <div class="outline-links">')

    in_front_matter = False  # collapsible front-matter chapter
    in_region = False        # region label (I-IV), not collapsible itself
    in_hike = False          # collapsible hike group

    for tag, slug, display, kind, hike_num in nav_items:
        if kind == "skip":
            continue

        if tag == "h2":
            # Close any open hike
            if in_hike:
                lines.append("      </details>")
                in_hike = False
            # Close any open front-matter chapter
            if in_front_matter:
                lines.append("    </details>")
                in_front_matter = False

            if is_region_chapter(slug):
                # Region header — just a label, not collapsible
                in_region = True
                lines.append(
                    f'    <div class="region-label"><a href="#{slug}">{display}</a></div>'
                )
            elif slug in ("bibliography", "acknowledgments"):
                # Back matter — simple link
                in_region = False
                lines.append(
                    f'    <a class="back-matter" href="#{slug}">{display}</a>'
                )
            else:
                # Front-matter chapter — collapsible
                in_region = False
                in_front_matter = True
                lines.append(f'    <details class="front-matter">')
                lines.append(
                    f'      <summary><a href="#{slug}">{display}</a></summary>'
                )

        elif tag == "h3":
            if kind == "hike":
                # Close previous hike if open
                if in_hike:
                    lines.append("      </details>")
                in_hike = True
                num_prefix = f"{hike_num}. " if hike_num else ""
                lines.append(f'      <details class="hike-group">')
                lines.append(
                    f'        <summary><a href="#{slug}">{num_prefix}{display}</a></summary>'
                )
            elif kind == "road":
                if in_front_matter or in_region:
                    lines.append(
                        f'      <a class="road-section" href="#{slug}">{display}</a>'
                    )
            elif kind == "section":
                if in_hike:
                    # Trail segment inside a hike
                    lines.append(
                        f'        <a href="#{slug}">{display}</a>'
                    )
                elif in_front_matter:
                    # Sub-section of a front-matter chapter
                    lines.append(
                        f'      <a href="#{slug}">{display}</a>'
                    )
                elif in_region:
                    # Narrative section at region level (e.g. "The Hole-In-The-Rock Expedition")
                    lines.append(
                        f'      <a class="narrative" href="#{slug}">{display}</a>'
                    )

    # Close any remaining open tags
    if in_hike:
        lines.append("      </details>")
    if in_front_matter:
        lines.append("    </details>")

    lines.append("  </div>")
    lines.append("</nav>")
    return "\n".join(lines)


def inject_styles_and_nav(html, nav_html):
    new_style = """<style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      max-width: 680px;
      margin: 0 auto;
      padding: 2rem 1rem 4rem;
      font: 18px/1.7 Georgia, 'Times New Roman', serif;
      color: #222;
      background: #fafaf8;
    }

    h1 {
      font-size: 1.8rem;
      margin-bottom: 2rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px solid #ccc;
    }

    h2 {
      font-size: 1.5rem;
      margin: 2.5rem 0 1rem;
      padding-top: 1rem;
      border-top: 2px solid #ddd;
    }

    h3 {
      font-size: 1.2rem;
      margin: 1.5rem 0 0.5rem;
    }

    p {
      margin-bottom: 0.8em;
      text-align: justify;
      hyphens: auto;
    }

    p.small {
      font-size: 0.85em;
      color: #444;
    }

    blockquote {
      margin: 1rem 2rem;
      font-style: italic;
      color: #555;
    }

    figure {
      margin: 1.5rem 0;
      text-align: center;
    }

    figure img {
      max-width: 100%;
      height: auto;
      border: 1px solid #ddd;
    }

    figcaption {
      font-size: 0.85em;
      color: #666;
      margin-top: 0.5rem;
    }

    /* ── Nav sidebar ── */
    nav.outline {
      position: fixed;
      left: 0;
      top: 0;
      width: 250px;
      height: 100vh;
      overflow-y: auto;
      padding: 1.25rem 0.75rem;
      background: #fafaf8;
      border-right: 1px solid #e0ddd8;
      font: 12.5px/1.5 -apple-system, system-ui, "Segoe UI", sans-serif;
      color: #555;
      z-index: 100;
    }

    nav.outline .outline-toggle {
      display: none;
    }

    nav.outline .outline-links {
      display: block !important;
    }

    /* Shared disclosure triangle */
    nav.outline summary {
      cursor: pointer;
      list-style: none;
    }
    nav.outline summary::-webkit-details-marker { display: none; }
    nav.outline summary::marker { display: none; content: ""; }
    nav.outline summary::before {
      content: "";
      display: inline-block;
      width: 0; height: 0;
      border-top: 3.5px solid transparent;
      border-bottom: 3.5px solid transparent;
      border-left: 4.5px solid #ccc;
      margin-right: 5px;
      vertical-align: middle;
      transition: transform 0.15s;
    }
    nav.outline details[open] > summary::before {
      transform: rotate(90deg);
    }
    nav.outline summary a {
      color: inherit;
      text-decoration: none;
    }
    nav.outline summary:hover { color: #0066cc; }

    /* Shared link style */
    nav.outline a {
      color: #666;
      text-decoration: none;
    }
    nav.outline a:hover {
      color: #0066cc;
    }

    /* ── Region labels (I-IV) ── */
    nav.outline .region-label {
      margin-top: 0.75rem;
      margin-bottom: 0.2rem;
      padding: 0.25rem 0;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      color: #777;
      border-top: 1px solid #e5e5e0;
    }

    nav.outline .region-label a { color: inherit; }

    /* ── Back matter links ── */
    nav.outline a.back-matter {
      display: block;
      padding: 0.15rem 0;
      margin-top: 0.4rem;
      color: #777;
      border-top: 1px solid #eee;
    }

    /* ── Front-matter chapters ── */
    nav.outline details.front-matter {
      margin-bottom: 1px;
    }

    nav.outline details.front-matter summary {
      padding: 0.2rem 0;
      color: #555;
    }

    nav.outline details.front-matter > a {
      display: block;
      padding: 1px 0 1px 1rem;
      color: #666;
      font-size: 11.5px;
    }

    /* ── Hike groups ── */
    nav.outline details.hike-group {
      margin-bottom: 1px;
    }

    nav.outline details.hike-group summary {
      padding: 0.2rem 0;
      font-weight: 600;
      color: #444;
    }

    /* Trail segments inside hikes */
    nav.outline details.hike-group > a {
      display: block;
      padding: 1px 0 1px 1.3rem;
      color: #666;
      font-size: 12px;
    }

    /* Road sections */
    nav.outline a.road-section {
      display: block;
      padding: 0.1rem 0;
      color: #888;
      font-size: 11.5px;
    }

    /* Narrative sections at region level */
    nav.outline a.narrative {
      display: block;
      padding: 0.1rem 0;
      color: #666;
      font-style: italic;
    }

    @media (min-width: 1250px) {
      body {
        margin-left: calc(250px + (100% - 250px - 680px) / 2);
      }
    }

    @media (max-width: 1249px) {
      nav.outline {
        position: fixed;
        left: 0; top: 0; right: 0;
        width: 100%;
        height: auto;
        max-height: 60vh;
        border-right: none;
        border-bottom: 1px solid #ddd;
        padding: 0;
        background: #fafaf8;
      }

      nav.outline .outline-toggle {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.6rem 1rem;
        cursor: pointer;
        background: #fafaf8;
        border-bottom: 1px solid #eee;
        font-weight: 600;
        font-size: 14px;
        color: #333;
      }

      nav.outline .outline-chevron {
        font-size: 0.65em;
        color: #999;
        transition: transform 0.2s;
      }

      nav.outline.open .outline-chevron {
        transform: rotate(180deg);
      }

      nav.outline .outline-links {
        display: none !important;
        padding: 0.5rem 1rem 0.75rem;
        overflow-y: auto;
        max-height: calc(60vh - 3rem);
      }

      nav.outline.open .outline-links {
        display: block !important;
      }

      body {
        padding-top: 3.5rem;
      }
    }
  </style>"""

    # Replace existing style block
    style_match = re.search(r"<style>.*?</style>", html, flags=re.DOTALL)
    if style_match:
        html = html[:style_match.start()] + new_style + html[style_match.end():]

    script = """<script>
(function() {
  var toggle = document.querySelector('.outline-toggle');
  var nav = document.querySelector('nav.outline');
  if (toggle) {
    toggle.addEventListener('click', function() {
      nav.classList.toggle('open');
    });
    nav.querySelectorAll('.outline-links a').forEach(function(a) {
      a.addEventListener('click', function() {
        nav.classList.remove('open');
      });
    });
  }
})();
</script>"""

    html = html.replace("<body>\n", f"<body>\n{nav_html}\n{script}\n", 1)

    # Add trips.js before </body>
    html = html.replace("</body>", '<script src="../trips.js"></script>\n</body>', 1)

    return html


if __name__ == "__main__":
    main()
