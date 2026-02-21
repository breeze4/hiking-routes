#!/usr/bin/env python3
"""Extract text (via OCR) and diagrams/maps from scanned PDFs."""

import argparse
import base64
import html
import re
import shutil
import sys
import tempfile
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import cv2
import fitz  # pymupdf
import numpy as np
import pytesseract
from PIL import Image


DPI = 300
# Edge density threshold for topo maps (lots of contour lines)
TOPO_EDGE_DENSITY_THRESH = 0.05
# Text density threshold for line-art maps (sparse lines, mostly white)
LINE_MAP_TEXT_DENSITY_THRESH = 0.04
# Blur kernel and threshold for photo detection via heavy blur
PHOTO_BLUR_KERNEL = 151
PHOTO_DARK_THRESH = 160
# Minimum fraction of page area for a photo region
MIN_PHOTO_FRACTION = 0.02
# Padding (pixels) around cropped photo regions
CROP_PAD = 20


class _EpubPageParser(HTMLParser):
    """Extract ordered blocks (text and images) from an EPUB page XHTML file."""

    # Marker characters for inline italic (survive html.escape)
    ITALIC_START = "\x01"
    ITALIC_END = "\x02"

    def __init__(self):
        super().__init__()
        self.blocks: list[dict] = []
        self._in_font = False
        self._skip_font = False
        self._font_size = 0
        self._in_italic = False
        self._current_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "font":
            color = attrs_dict.get("color", "").upper()
            size = attrs_dict.get("size", "")
            if color == "#FF0000" or size == "0":
                self._skip_font = True
            else:
                self._in_font = True
                self._skip_font = False
                self._font_size = int(size) if size.isdigit() else 3

        elif tag == "img":
            src = attrs_dict.get("src", "")
            width = int(attrs_dict.get("width", "0"))
            height = int(attrs_dict.get("height", "0"))
            # Filter spacer GIFs (tiny layout images)
            if width > 10 and height > 10:
                self.blocks.append(
                    {"type": "image", "src": src, "width": width, "height": height}
                )

        elif tag == "br":
            if self._in_font:
                self._current_text.append("\n")

        elif tag == "i":
            if self._in_font:
                self._in_italic = True
                self._current_text.append(self.ITALIC_START)

    def handle_endtag(self, tag):
        if tag == "font":
            if self._in_font and self._current_text:
                text = "".join(self._current_text).strip()
                if text:
                    has_italic = self.ITALIC_START in text
                    self.blocks.append({
                        "type": "text",
                        "text": text,
                        "size": self._font_size,
                        "has_italic": has_italic,
                    })
                self._current_text = []
            self._in_font = False
            self._skip_font = False

        elif tag == "i":
            if self._in_font and self._in_italic:
                self._current_text.append(self.ITALIC_END)
                self._in_italic = False

    def handle_data(self, data):
        if self._in_font and not self._skip_font:
            self._current_text.append(data)


def parse_epub_page(xml_content: str) -> list[dict]:
    """Parse a single EPUB page XML and return ordered blocks."""
    parser = _EpubPageParser()
    parser.feed(xml_content)
    return parser.blocks


def render_pages(pdf_path: Path, output_dir: Path) -> list[Path]:
    """Render each page of a PDF to a 300-DPI PNG."""
    pages_dir = output_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    zoom = DPI / 72  # 72 is the default PDF DPI
    mat = fitz.Matrix(zoom, zoom)
    page_images = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        out_path = pages_dir / f"page_{i + 1:03d}.png"
        pix.save(str(out_path))
        page_images.append(out_path)
        print(f"  Rendered page {i + 1}/{len(doc)}")

    doc.close()
    return page_images


def ocr_pages(page_images: list[Path], output_dir: Path) -> None:
    """Run OCR on each rendered page image and write text files."""
    text_dir = output_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)

    all_text = []
    for img_path in page_images:
        page_num = img_path.stem  # e.g. page_001
        img = Image.open(img_path)
        text = pytesseract.image_to_string(img)

        per_page = text_dir / f"{page_num}.txt"
        per_page.write_text(text, encoding="utf-8")
        all_text.append(text)
        print(f"  OCR'd {page_num}")

    combined = output_dir / "text.txt"
    combined.write_text("\n\n".join(all_text), encoding="utf-8")
    print(f"  Combined text written to {combined}")


def _is_full_page_map(gray: np.ndarray) -> bool:
    """Detect full-page maps: topo maps (high edge density) or line-art maps (sparse content)."""
    h, w = gray.shape

    edges = cv2.Canny(gray, 50, 150)
    edge_density = edges.sum() / (h * w * 255)
    if edge_density > TOPO_EDGE_DENSITY_THRESH:
        return True

    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    text_density = binary.sum() / (h * w * 255)
    if text_density < LINE_MAP_TEXT_DENSITY_THRESH and edge_density < 0.02:
        return True

    return False


def _find_photo_regions(gray: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Find photo regions using heavy blur + dark threshold.

    Photos remain dark after heavy Gaussian blur, while text and white space
    become near-white. Threshold the blurred image to find dark rectangular
    regions = photos.
    """
    h, w = gray.shape
    page_area = h * w

    k = PHOTO_BLUR_KERNEL
    blurred = cv2.GaussianBlur(gray, (k, k), 0)
    _, dark_mask = cv2.threshold(blurred, PHOTO_DARK_THRESH, 255, cv2.THRESH_BINARY_INV)

    # Close small gaps within photo regions
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 50))
    closed = cv2.morphologyEx(dark_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < page_area * MIN_PHOTO_FRACTION:
            continue
        x, y, cw, ch = cv2.boundingRect(contour)
        x1 = max(0, x - CROP_PAD)
        y1 = max(0, y - CROP_PAD)
        x2 = min(w, x + cw + CROP_PAD)
        y2 = min(h, y + ch + CROP_PAD)
        regions.append((x1, y1, x2, y2))

    return regions


def detect_diagrams(page_images: list[Path], output_dir: Path) -> None:
    """Detect maps and photos, saving them as separate images."""
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    total_found = 0
    for img_path in page_images:
        page_num = img_path.stem
        img = cv2.imread(str(img_path))
        if img is None:
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        saved = 0

        # Check for full-page maps (topo or line-art)
        if _is_full_page_map(gray):
            out_path = images_dir / f"{page_num}_map.png"
            cv2.imwrite(str(out_path), img)
            saved += 1
        else:
            # Look for embedded photo regions
            for i, (x1, y1, x2, y2) in enumerate(_find_photo_regions(gray), 1):
                region = img[y1:y2, x1:x2]
                out_path = images_dir / f"{page_num}_photo_{i}.png"
                cv2.imwrite(str(out_path), region)
                saved += 1

        if saved > 0:
            total_found += saved
            print(f"  {page_num}: {saved} image(s)")

    print(f"  Total images extracted: {total_found}")


_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
}


def _img_to_data_uri(img_path: Path) -> str:
    """Convert an image file to a base64 data URI."""
    mime = _MIME_TYPES.get(img_path.suffix.lower(), "image/png")
    data = img_path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


def build_html(output_dir: Path) -> None:
    """Build a single self-contained HTML file from extracted text and images."""
    text_dir = output_dir / "text"
    images_dir = output_dir / "images"
    title = output_dir.name

    # Collect per-page text files
    text_files = sorted(text_dir.glob("page_*.txt"))

    # Index images by page number
    page_images: dict[str, list[Path]] = {}
    if images_dir.exists():
        for img_path in sorted(images_dir.glob("page_*")):
            m = re.match(r"(page_\d+)", img_path.name)
            if m:
                page_images.setdefault(m.group(1), []).append(img_path)

    # Determine which pages are map-only (image name contains _map)
    map_pages = set()
    if images_dir.exists():
        for img_path in images_dir.glob("*_map.*"):
            m = re.match(r"(page_\d+)", img_path.name)
            if m:
                map_pages.add(m.group(1))

    parts = []
    for text_file in text_files:
        page_key = text_file.stem  # e.g. page_001
        page_num = int(page_key.split("_")[1])
        text = text_file.read_text(encoding="utf-8").strip()
        imgs = page_images.get(page_key, [])

        # Skip empty pages with no images
        if not text and not imgs:
            continue

        parts.append(f'<section class="page" id="{page_key}">')

        if page_key in map_pages:
            # Map page: show image only, skip garbage OCR
            for img_path in imgs:
                uri = _img_to_data_uri(img_path)
                parts.append(f'<figure><img src="{uri}" alt="Map — page {page_num}"></figure>')
        else:
            # Text page, possibly with embedded photos
            # Photos go before the text block
            for img_path in imgs:
                uri = _img_to_data_uri(img_path)
                parts.append(f'<figure><img src="{uri}" alt="Photo — page {page_num}"></figure>')

            if text:
                # Clean up OCR artifacts: strip page numbers and repeated
                # headers from the top of each page
                lines = text.split("\n")
                # Strip leading noise lines (page numbers, blank lines,
                # repeated "Muddy Creek" header)
                while lines:
                    s = lines[0].strip()
                    if not s or s.isdigit() or s == "Muddy Creek" or s == "|":
                        lines.pop(0)
                    else:
                        break

                cleaned = "\n".join(lines).strip()
                if cleaned:
                    escaped = html.escape(cleaned)
                    # Convert double newlines to paragraph breaks
                    paragraphs = [p.strip() for p in escaped.split("\n\n") if p.strip()]
                    for p in paragraphs:
                        # Join soft-wrapped lines within a paragraph
                        joined = " ".join(p.split("\n"))
                        parts.append(f"<p>{joined}</p>")

        parts.append("</section>")

    body = "\n".join(parts)

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    max-width: 680px;
    margin: 0 auto;
    padding: 2rem 1rem 4rem;
    font: 18px/1.7 Georgia, 'Times New Roman', serif;
    color: #222;
    background: #fafaf8;
  }}
  h1 {{
    font-size: 1.8rem;
    margin-bottom: 2rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #ccc;
  }}
  section.page {{
    margin-bottom: 1.5rem;
  }}
  section.page + section.page {{
    padding-top: 1rem;
    border-top: 1px solid #e8e8e4;
  }}
  p {{
    margin-bottom: 0.8em;
    text-align: justify;
    hyphens: auto;
  }}
  figure {{
    margin: 1.5rem 0;
    text-align: center;
  }}
  figure img {{
    max-width: 100%;
    height: auto;
    border: 1px solid #ddd;
  }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
{body}
</body>
</html>"""

    out_path = output_dir / "index.html"
    out_path.write_text(doc, encoding="utf-8")
    print(f"  HTML written to {out_path}")


def _epub_text_to_html(text: str) -> str:
    """Convert EPUB text block to HTML, preserving italic markers and line breaks."""
    escaped = html.escape(text)
    escaped = escaped.replace(_EpubPageParser.ITALIC_START, "<em>")
    escaped = escaped.replace(_EpubPageParser.ITALIC_END, "</em>")
    escaped = escaped.replace("\n", "<br>")
    return escaped


def _build_epub_html(
    pages_data: list[list[dict]], images_dir: Path, title: str, output_path: Path
) -> None:
    """Build HTML from structured EPUB page data."""
    parts = []

    for blocks in pages_data:
        i = 0
        while i < len(blocks):
            block = blocks[i]

            if block["type"] == "image":
                img_path = block.get("path")
                if img_path and img_path.exists():
                    uri = _img_to_data_uri(img_path)
                    # Check if next block is a size-2 caption
                    caption = None
                    if i + 1 < len(blocks):
                        nxt = blocks[i + 1]
                        if nxt["type"] == "text" and nxt["size"] == 2:
                            caption = nxt
                            i += 1
                    parts.append("<figure>")
                    parts.append(f'<img src="{uri}" alt="">')
                    if caption:
                        parts.append(
                            f"<figcaption>{_epub_text_to_html(caption['text'])}</figcaption>"
                        )
                    parts.append("</figure>")

            elif block["type"] == "text":
                text_html = _epub_text_to_html(block["text"])
                size = block["size"]

                if size == 4:
                    parts.append(f"<h2>{text_html}</h2>")
                elif size == 3:
                    plain = (
                        block["text"]
                        .replace(_EpubPageParser.ITALIC_START, "")
                        .replace(_EpubPageParser.ITALIC_END, "")
                    )
                    if len(plain) <= 50 and "." not in plain:
                        parts.append(f"<h3>{text_html}</h3>")
                    else:
                        parts.append(f"<p>{text_html}</p>")
                elif size == 2:
                    if block["text"].startswith(_EpubPageParser.ITALIC_START):
                        parts.append(f"<blockquote>{text_html}</blockquote>")
                    else:
                        parts.append(f'<p class="small">{text_html}</p>')

            i += 1

    body = "\n".join(parts)

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    max-width: 680px;
    margin: 0 auto;
    padding: 2rem 1rem 4rem;
    font: 18px/1.7 Georgia, 'Times New Roman', serif;
    color: #222;
    background: #fafaf8;
  }}
  h1 {{
    font-size: 1.8rem;
    margin-bottom: 2rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #ccc;
  }}
  h2 {{
    font-size: 1.5rem;
    margin: 2rem 0 1rem;
  }}
  h3 {{
    font-size: 1.2rem;
    margin: 1.5rem 0 0.5rem;
  }}
  p {{
    margin-bottom: 0.8em;
    text-align: justify;
    hyphens: auto;
  }}
  p.small {{
    font-size: 0.85em;
    color: #444;
  }}
  blockquote {{
    margin: 1rem 2rem;
    font-style: italic;
    color: #555;
  }}
  figure {{
    margin: 1.5rem 0;
    text-align: center;
  }}
  figure img {{
    max-width: 100%;
    height: auto;
    border: 1px solid #ddd;
  }}
  figcaption {{
    font-size: 0.85em;
    color: #666;
    margin-top: 0.5rem;
  }}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
{body}
</body>
</html>"""

    output_path.write_text(doc, encoding="utf-8")
    print(f"  HTML written to {output_path}")


def process_pdf(pdf_path: Path, output_base: Path) -> None:
    """Full pipeline for a single PDF."""
    name = pdf_path.stem
    output_dir = output_base / name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Processing: {pdf_path.name} ===")

    print("\n[1/4] Rendering pages...")
    page_images = render_pages(pdf_path, output_dir)

    print("\n[2/4] Running OCR...")
    ocr_pages(page_images, output_dir)

    print("\n[3/4] Detecting diagrams...")
    detect_diagrams(page_images, output_dir)

    print("\n[4/4] Building HTML...")
    build_html(output_dir)

    print(f"\nDone. Output in: {output_dir}")


def process_epub(epub_path: Path, output_base: Path, page_start: int, page_end: int) -> None:
    """Full pipeline for an EPUB file over a page range."""
    name = epub_path.stem
    output_dir = output_base / name
    text_dir = output_dir / "text"
    images_dir = output_dir / "images"
    text_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Processing: {epub_path.name} (pages {page_start}-{page_end}) ===")

    pages_data: list[list[dict]] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        print("\n[1/3] Extracting EPUB...")
        with zipfile.ZipFile(epub_path) as zf:
            zf.extractall(tmp_path)
        content_dir = tmp_path / "content"

        all_text = []
        for page_num in range(page_start, page_end + 1):
            page_xml = content_dir / f"page_{page_num}.xml"
            if not page_xml.exists():
                print(f"  Warning: {page_xml.name} not found, skipping")
                continue

            xml_content = page_xml.read_text(encoding="utf-8")
            blocks = parse_epub_page(xml_content)
            page_key = f"page_{page_num:03d}"

            # Write per-page text (strip italic markers for plain text output)
            text_parts = []
            for block in blocks:
                if block["type"] == "text":
                    plain = (
                        block["text"]
                        .replace(_EpubPageParser.ITALIC_START, "")
                        .replace(_EpubPageParser.ITALIC_END, "")
                    )
                    text_parts.append(plain)
            page_text = "\n".join(text_parts)
            (text_dir / f"{page_key}.txt").write_text(page_text, encoding="utf-8")
            all_text.append(page_text)

            # Copy images and store output paths in blocks
            img_idx = 0
            n_text = sum(1 for b in blocks if b["type"] == "text")
            for block in blocks:
                if block["type"] == "image":
                    img_idx += 1
                    src_path = content_dir / block["src"]
                    if src_path.exists():
                        ext = src_path.suffix
                        dst = images_dir / f"{page_key}_img_{img_idx}{ext}"
                        shutil.copy2(src_path, dst)
                        block["path"] = dst
                        print(f"  {page_key}: image {block['src']} -> {dst.name}")

            pages_data.append(blocks)
            print(f"  Parsed {page_xml.name}: {n_text} text blocks, {img_idx} images")

        # Combined text
        print("\n[2/3] Writing combined text...")
        combined = output_dir / "text.txt"
        combined.write_text("\n\n".join(all_text), encoding="utf-8")
        print(f"  Combined text written to {combined}")

    print("\n[3/3] Building HTML...")
    _build_epub_html(pages_data, images_dir, name, output_dir / "index.html")
    print(f"\nDone. Output in: {output_dir}")


def _process_file(file_path: Path, output_base: Path, pages: str | None) -> None:
    """Route a file to the appropriate processor based on extension."""
    ext = file_path.suffix.lower()
    if ext == ".epub":
        if not pages:
            print("Error: --pages START-END is required for EPUB files", file=sys.stderr)
            sys.exit(1)
        m = re.match(r"(\d+)-(\d+)$", pages)
        if not m:
            print("Error: --pages must be in START-END format (e.g. 28-49)", file=sys.stderr)
            sys.exit(1)
        process_epub(file_path, output_base, int(m.group(1)), int(m.group(2)))
    elif ext == ".pdf":
        process_pdf(file_path, output_base)
    else:
        print(f"Error: unsupported file type {ext}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Extract text and diagrams from PDFs and EPUBs")
    parser.add_argument("input", nargs="?", help="Path to a PDF or EPUB file (default: all in input/)")
    parser.add_argument("--pages", help="Page range for EPUB extraction (e.g. 28-49)")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    output_base = script_dir / "output"

    if args.input:
        file_path = Path(args.input)
        if not file_path.exists():
            print(f"Error: {file_path} not found", file=sys.stderr)
            sys.exit(1)
        _process_file(file_path, output_base, args.pages)
    else:
        input_dir = script_dir / "input"
        files = sorted(input_dir.glob("*.pdf")) + sorted(input_dir.glob("*.epub"))
        if not files:
            print(f"No PDF/EPUB files found in {input_dir}", file=sys.stderr)
            sys.exit(1)
        for file_path in files:
            _process_file(file_path, output_base, args.pages)


if __name__ == "__main__":
    main()
