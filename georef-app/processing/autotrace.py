"""Auto-trace image processing pipeline. Pure computation, no web dependencies."""

import cv2
import numpy as np


def _auto_threshold(gray: np.ndarray) -> int:
    """Find the darkest palette level in a GIF image."""
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    for i in range(256):
        if hist[i] > 50:
            return i + 5
    return 30


def _remove_borders(binary: np.ndarray) -> np.ndarray:
    """Remove components connected to the image border via flood fill."""
    result = binary.copy()
    h, w = result.shape
    for y in range(h):
        if result[y, 0] > 0:
            cv2.floodFill(result, None, (0, y), 0)
        if result[y, w - 1] > 0:
            cv2.floodFill(result, None, (w - 1, y), 0)
    for x in range(w):
        if result[0, x] > 0:
            cv2.floodFill(result, None, (x, 0), 0)
        if result[h - 1, x] > 0:
            cv2.floodFill(result, None, (x, h - 1), 0)
    return result


def _morphological_thin(binary: np.ndarray) -> np.ndarray:
    """Skeletonize via iterative hit-or-miss thinning."""
    elements = []
    e1 = np.array([[-1, -1, -1], [0, 1, 0], [1, 1, 1]], dtype=np.int8)
    e2 = np.array([[0, -1, -1], [1, 1, -1], [0, 1, 0]], dtype=np.int8)
    for _ in range(4):
        elements.append(e1.copy())
        elements.append(e2.copy())
        e1 = np.rot90(e1)
        e2 = np.rot90(e2)

    result = binary.copy()
    for _ in range(100):
        prev = result.copy()
        for elem in elements:
            hitmiss = cv2.morphologyEx(result, cv2.MORPH_HITMISS, elem)
            result = result - hitmiss
        if np.array_equal(result, prev):
            break
    return result


def _prune_branches(skeleton: np.ndarray, iterations: int = 20) -> np.ndarray:
    """Remove short branches by iteratively removing endpoint pixels."""
    result = skeleton.copy()
    for _ in range(iterations):
        coords = np.argwhere(result > 0)
        to_remove = []
        for py, px in coords:
            patch = result[max(0, py - 1):py + 2, max(0, px - 1):px + 2]
            if np.count_nonzero(patch) - 1 == 1:  # endpoint
                to_remove.append((py, px))
        if not to_remove:
            break
        for py, px in to_remove:
            result[py, px] = 0
    return result


def _find_longest_path(skeleton: np.ndarray) -> list[tuple[int, int]]:
    """Find the longest path through a skeleton component using double-BFS."""
    coords = set(map(tuple, np.argwhere(skeleton > 0)))
    if not coords:
        return []

    def neighbors(pt):
        y, x = pt
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                n = (y + dy, x + dx)
                if n in coords:
                    yield n

    endpoints = [p for p in coords if sum(1 for _ in neighbors(p)) == 1]
    if not endpoints:
        endpoints = [next(iter(coords))]

    def bfs(start):
        visited = {start: None}
        queue = [start]
        last = start
        while queue:
            current = queue.pop(0)
            last = current
            for n in neighbors(current):
                if n not in visited:
                    visited[n] = current
                    queue.append(n)
        path = []
        node = last
        while node is not None:
            path.append(node)
            node = visited[node]
        return path[::-1], last

    _, far1 = bfs(endpoints[0])
    path, _ = bfs(far1)
    return path


def _preprocess(image_path: str, dark_threshold: int | None = None,
                close_kernel: int = 11) -> tuple[np.ndarray, np.ndarray] | tuple[None, None]:
    """Shared preprocessing: load -> threshold -> close -> border removal."""
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return None, None

    if dark_threshold is None:
        dark_threshold = _auto_threshold(gray)

    _, binary = cv2.threshold(gray, dark_threshold, 255, cv2.THRESH_BINARY_INV)

    if close_kernel > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_kernel, close_kernel))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    binary = _remove_borders(binary)
    return binary, gray


def extract_routes(image_path: str, dark_threshold: int | None = None,
                   close_kernel: int = 11, min_area: int = 200,
                   prune_iterations: int = 20,
                   simplify_epsilon: float = 3.0,
                   _debug: bool = False) -> list[dict] | tuple[list[dict], np.ndarray]:
    """Full auto-trace pipeline: threshold -> close -> border removal -> components -> thin -> trace."""
    binary, gray = _preprocess(image_path, dark_threshold, close_kernel)
    if binary is None:
        return ([], None) if _debug else []
    debug_binary = binary.copy() if _debug else None

    img_h, img_w = binary.shape
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
    order = np.argsort(-stats[1:, cv2.CC_STAT_AREA]) + 1

    routes = []
    for idx in order:
        area = int(stats[idx, cv2.CC_STAT_AREA])
        if area < min_area:
            break

        x, y, w, h = [int(v) for v in stats[idx, :4]]

        # Filter border artifacts: thin strips near image edge
        aspect = max(w, h) / max(min(w, h), 1)
        near_edge = (x < 5 or y < 5 or x + w > img_w - 5 or y + h > img_h - 5)
        if aspect > 20 and near_edge:
            continue

        mask = (labels == idx).astype(np.uint8) * 255
        skeleton = _morphological_thin(mask)
        pruned = _prune_branches(skeleton, prune_iterations)

        remaining = int(np.count_nonzero(pruned))
        if remaining < 30:
            continue

        path = _find_longest_path(pruned)
        if len(path) < 10:
            continue

        pts = np.array([[p[1], p[0]] for p in path], dtype=np.float32).reshape(-1, 1, 2)
        simplified = cv2.approxPolyDP(pts, simplify_epsilon, closed=False)
        points = [{"px": int(p[0]), "py": int(p[1])} for p in simplified.reshape(-1, 2)]

        routes.append({
            "id": len(routes),
            "points": points,
            "length_px": len(path),
            "bbox": {"x": x, "y": y, "w": w, "h": h},
            "area": area,
        })

    if _debug:
        return routes, debug_binary
    return routes
