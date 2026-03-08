/**
 * Canvas rendering, pan/zoom, coordinate transforms, draw hook system.
 */

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const wrap = document.getElementById('canvas-wrap');

let img = null;
let scale = 1;
let offsetX = 0, offsetY = 0;
let dragging = false;
let dragStartX, dragStartY, dragOffsetX, dragOffsetY;

// Draw hooks: other modules register functions to draw their overlays
const drawHooks = [];
// Click handlers: keyed by mode name
const clickHandlers = {};

export function getImg() { return img; }
export function getImgSize() { return img ? { w: img.width, h: img.height } : null; }
export function getScale() { return scale; }
export function getOffset() { return { x: offsetX, y: offsetY }; }

export function setImg(newImg) { img = newImg; }

export function onDraw(fn) { drawHooks.push(fn); }
export function onCanvasClick(mode, fn) { clickHandlers[mode] = fn; }

export function screenToImage(sx, sy) {
  return { x: (sx - offsetX) / scale, y: (sy - offsetY) / scale };
}

export function imageToScreen(px, py) {
  return { x: px * scale + offsetX, y: py * scale + offsetY };
}

export function resetView() {
  const w = wrap.clientWidth;
  const h = wrap.clientHeight;
  canvas.width = w;
  canvas.height = h;
  if (!img) return;
  scale = Math.min(w / img.width, h / img.height) * 0.95;
  offsetX = (w - img.width * scale) / 2;
  offsetY = (h - img.height * scale) / 2;
  draw();
}

export function draw() {
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (!img) return;

  ctx.save();
  ctx.translate(offsetX, offsetY);
  ctx.scale(scale, scale);
  ctx.drawImage(img, 0, 0);
  ctx.restore();

  for (const hook of drawHooks) {
    hook(ctx, scale, offsetX, offsetY);
  }
}

// --- Mouse handlers ---

let currentMode = 'gcp';
export function setCurrentMode(mode) { currentMode = mode; }

canvas.addEventListener('mousedown', (e) => {
  if (e.button === 1 || e.button === 2 || e.shiftKey) {
    dragging = true;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragOffsetX = offsetX;
    dragOffsetY = offsetY;
    canvas.style.cursor = 'grabbing';
    e.preventDefault();
    return;
  }
  if (e.button === 0 && !e.shiftKey) {
    const rect = canvas.getBoundingClientRect();
    const pt = screenToImage(e.clientX - rect.left, e.clientY - rect.top);
    if (pt.x < 0 || pt.y < 0 || !img || pt.x > img.width || pt.y > img.height) return;

    const handler = clickHandlers[currentMode];
    if (handler) handler(pt);
    draw();
  }
});

canvas.addEventListener('mousemove', (e) => {
  if (dragging) {
    offsetX = dragOffsetX + (e.clientX - dragStartX);
    offsetY = dragOffsetY + (e.clientY - dragStartY);
    draw();
    return;
  }
});

canvas.addEventListener('mouseup', () => {
  dragging = false;
  canvas.style.cursor = 'crosshair';
});

canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;

  const zoomFactor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
  const newScale = scale * zoomFactor;

  offsetX = mx - (mx - offsetX) * (newScale / scale);
  offsetY = my - (my - offsetY) * (newScale / scale);
  scale = newScale;
  draw();
}, { passive: false });

canvas.addEventListener('contextmenu', (e) => e.preventDefault());

window.addEventListener('resize', () => {
  if (img) {
    canvas.width = wrap.clientWidth;
    canvas.height = wrap.clientHeight;
    draw();
  }
});

// Expose mousemove for status bar updates
let mouseMoveHandler = null;
export function onMouseMove(fn) { mouseMoveHandler = fn; }

canvas.addEventListener('mousemove', (e) => {
  if (dragging) return;
  if (mouseMoveHandler && img) {
    const rect = canvas.getBoundingClientRect();
    const pt = screenToImage(e.clientX - rect.left, e.clientY - rect.top);
    if (pt.x >= 0 && pt.y >= 0 && pt.x <= img.width && pt.y <= img.height) {
      mouseMoveHandler(pt);
    }
  }
});
