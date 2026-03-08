/**
 * Auto-trace: automatic route detection from map images.
 */

import { onDraw, imageToScreen, draw } from './canvas.js';
import { fetchAutoTrace } from './api.js';
import { setStatus, markDirty } from './persistence.js';
import { getWaypoints, updateWPTable } from './trace.js';

const AUTO_COLORS = ['#ff6600', '#ff00cc', '#00ccff', '#ccff00', '#ff3333', '#33ff99'];
let autoRoutes = [];

export function getAutoRoutes() { return autoRoutes; }

export async function runAutoTrace(imgName) {
  if (!imgName) { setStatus('Load an image first'); return; }
  setStatus('Detecting routes...');

  const threshVal = document.getElementById('at-threshold').value;
  const body = {
    image_name: imgName,
    dark_threshold: threshVal ? parseInt(threshVal) : null,
    close_kernel: parseInt(document.getElementById('at-bridge').value) || 11,
    min_area: parseInt(document.getElementById('at-min-area').value) || 200,
    prune_iterations: parseInt(document.getElementById('at-prune').value) || 20,
    simplify_epsilon: parseFloat(document.getElementById('at-epsilon').value) || 3.0,
  };

  const data = await fetchAutoTrace(body);
  if (data.error) { setStatus(`Error: ${data.error}`); return; }

  autoRoutes = (data.routes || []).map((r, i) => ({
    ...r,
    color: AUTO_COLORS[i % AUTO_COLORS.length],
  }));

  updateAutoRouteList();
  draw();
  setStatus(`Detected ${autoRoutes.length} route(s) (threshold: ${data.threshold_used})`);
}

export function acceptAutoRoute(idx) {
  const route = autoRoutes[idx];
  if (!route) return;
  const waypoints = getWaypoints();
  const startIdx = waypoints.length;
  for (let i = 0; i < route.points.length; i++) {
    const p = route.points[i];
    waypoints.push({
      px: p.px, py: p.py,
      name: `AT${String(startIdx + i + 1).padStart(3, '0')}`,
      idx: startIdx + i,
    });
  }
  autoRoutes.splice(idx, 1);
  markDirty();
  updateAutoRouteList();
  updateWPTable();
  draw();
  setStatus(`Accepted route: ${route.points.length} waypoints added`);
}

export function rejectAutoRoute(idx) {
  autoRoutes.splice(idx, 1);
  updateAutoRouteList();
  draw();
}

function updateAutoRouteList() {
  const container = document.getElementById('auto-routes');
  container.innerHTML = '';
  for (let i = 0; i < autoRoutes.length; i++) {
    const r = autoRoutes[i];
    const div = document.createElement('div');
    div.className = 'auto-route-item';
    div.innerHTML = `
      <div class="swatch" style="background:${r.color}"></div>
      <div class="info">${r.points.length} pts, ${r.length_px}px path</div>
      <button class="btn-accept" data-idx="${i}">Accept</button>
      <button class="btn-reject" data-idx="${i}">X</button>
    `;
    container.appendChild(div);
  }
  // Event delegation
  container.querySelectorAll('.btn-accept').forEach(btn => {
    btn.addEventListener('click', () => acceptAutoRoute(parseInt(btn.dataset.idx)));
  });
  container.querySelectorAll('.btn-reject').forEach(btn => {
    btn.addEventListener('click', () => rejectAutoRoute(parseInt(btn.dataset.idx)));
  });
}

// --- Draw hook ---

onDraw((ctx, scale, ox, oy) => {
  for (const route of autoRoutes) {
    if (route.points.length < 2) continue;
    ctx.beginPath();
    ctx.strokeStyle = route.color;
    ctx.lineWidth = 3;
    ctx.globalAlpha = 0.7;
    const s0 = imageToScreen(route.points[0].px, route.points[0].py);
    ctx.moveTo(s0.x, s0.y);
    for (let i = 1; i < route.points.length; i++) {
      const s = imageToScreen(route.points[i].px, route.points[i].py);
      ctx.lineTo(s.x, s.y);
    }
    ctx.stroke();
    ctx.globalAlpha = 1.0;

    for (const p of route.points) {
      const s = imageToScreen(p.px, p.py);
      ctx.beginPath();
      ctx.arc(s.x, s.y, 3, 0, Math.PI * 2);
      ctx.fillStyle = route.color;
      ctx.fill();
    }
  }
});
