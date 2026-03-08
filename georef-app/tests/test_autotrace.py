#!/usr/bin/env python3
"""Auto-trace test report generator.

Runs the autotrace pipeline on all map images and produces a self-contained
HTML report showing three stages per image: original, binary mask, and
final overlay with route legend.

Usage:
    python3 georef-app/tests/test_autotrace.py [--images DIR] [--output FILE]
"""

import argparse
import base64
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from processing.autotrace import extract_routes

COLORS_HEX = ['#ff6600', '#ff00cc', '#00ccff', '#ccff00', '#ff3333', '#33ff99']
COLORS_BGR = []
for h in COLORS_HEX:
    r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
    COLORS_BGR.append((b, g, r))

EXTENSIONS = {'.gif', '.jpg', '.png'}


def img_to_data_uri(img: np.ndarray) -> str:
    _, buf = cv2.imencode('.png', img)
    b64 = base64.b64encode(buf).decode('ascii')
    return f'data:image/png;base64,{b64}'


def draw_overlay(original: np.ndarray, routes: list[dict]) -> np.ndarray:
    overlay = original.copy()
    if len(overlay.shape) == 2:
        overlay = cv2.cvtColor(overlay, cv2.COLOR_GRAY2BGR)
    for i, route in enumerate(routes):
        color = COLORS_BGR[i % len(COLORS_BGR)]
        pts = np.array([[p['px'], p['py']] for p in route['points']], dtype=np.int32)
        if len(pts) >= 2:
            cv2.polylines(overlay, [pts], isClosed=False, color=color, thickness=2)
        for p in pts:
            cv2.circle(overlay, tuple(p), 3, color, -1)
    return overlay


def binary_to_rgb(binary: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


def load_ignore_list(image_dir: Path) -> set[str]:
    ignore_file = image_dir / '.autotrace_ignore'
    if not ignore_file.exists():
        return set()
    return {line.strip() for line in ignore_file.read_text().splitlines()
            if line.strip() and not line.startswith('#')}


def build_report(image_dir: Path, output_path: Path):
    ignore = load_ignore_list(image_dir)
    images = sorted(p for p in image_dir.iterdir()
                    if p.suffix.lower() in EXTENSIONS and p.name not in ignore)
    if ignore:
        print(f'Ignoring {len(ignore)} images from .autotrace_ignore')
    if not images:
        print(f'No images found in {image_dir}')
        return

    sections = []
    total_routes = 0

    for img_path in images:
        print(f'Processing {img_path.name}...', end=' ')
        original = cv2.imread(str(img_path))
        if original is None:
            print('SKIP (unreadable)')
            continue

        routes, binary = extract_routes(str(img_path), _debug=True)
        total_routes += len(routes)
        substantial = [r for r in routes if r['length_px'] > 50]

        overlay = draw_overlay(original, routes)
        binary_rgb = binary_to_rgb(binary)

        orig_uri = img_to_data_uri(original)
        binary_uri = img_to_data_uri(binary_rgb)
        overlay_uri = img_to_data_uri(overlay)

        legend_rows = []
        for i, r in enumerate(routes):
            color = COLORS_HEX[i % len(COLORS_HEX)]
            legend_rows.append(
                f'<tr>'
                f'<td><span class="swatch" style="background:{color}"></span></td>'
                f'<td>Route {r["id"]}</td>'
                f'<td>{len(r["points"])} pts</td>'
                f'<td>{r["length_px"]}px</td>'
                f'<td>{r["area"]} area</td>'
                f'</tr>'
            )

        sections.append(f'''
<div class="section">
  <h2>{img_path.name}</h2>
  <div class="stats">{len(routes)} routes, {len(substantial)} substantial (&gt;50px path)</div>
  <div class="images">
    <div class="img-box">
      <h3>Original</h3>
      <img src="{orig_uri}">
    </div>
    <div class="img-box">
      <h3>Binary Mask</h3>
      <img src="{binary_uri}">
    </div>
    <div class="img-box">
      <h3>Detected Routes</h3>
      <img src="{overlay_uri}">
    </div>
  </div>
  <table class="legend">
    <thead><tr><th></th><th>ID</th><th>Points</th><th>Path</th><th>Area</th></tr></thead>
    <tbody>{''.join(legend_rows)}</tbody>
  </table>
</div>''')
        print(f'{len(routes)} routes')

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Autotrace Test Report</title>
<style>
body {{ font-family: system-ui, sans-serif; background: #1a1a2e; color: #e0e0e0; margin: 0; padding: 20px; }}
h1 {{ border-bottom: 1px solid #444; padding-bottom: 8px; }}
.summary {{ color: #aaa; margin-bottom: 20px; }}
.section {{ background: #16213e; border-radius: 8px; padding: 16px; margin-bottom: 24px; }}
.section h2 {{ margin-top: 0; color: #e0e0e0; font-size: 16px; }}
.stats {{ color: #888; font-size: 13px; margin-bottom: 8px; }}
.images {{ display: flex; gap: 12px; overflow-x: auto; }}
.img-box {{ flex: 0 0 auto; }}
.img-box h3 {{ font-size: 12px; color: #888; margin: 0 0 4px 0; }}
.img-box img {{ max-height: 400px; border: 1px solid #333; border-radius: 4px; }}
.legend {{ margin-top: 8px; font-size: 12px; border-collapse: collapse; }}
.legend th, .legend td {{ padding: 2px 8px; text-align: left; }}
.legend th {{ color: #888; }}
.swatch {{ display: inline-block; width: 14px; height: 14px; border-radius: 2px; vertical-align: middle; }}
</style>
</head>
<body>
<h1>Autotrace Test Report</h1>
<div class="summary">{len(images)} images processed, {total_routes} total routes detected</div>
{''.join(sections)}
</body>
</html>'''

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)
    print(f'\nReport: {output_path} ({output_path.stat().st_size // 1024}KB)')


def main():
    parser = argparse.ArgumentParser(description='Autotrace test report')
    parser.add_argument('--images', type=Path, default=Path('html/stevens-canyon/images'))
    parser.add_argument('--output', type=Path, default=Path('tmp/autotrace_report.html'))
    args = parser.parse_args()
    build_report(args.images, args.output)


if __name__ == '__main__':
    main()
