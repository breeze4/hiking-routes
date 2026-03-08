/**
 * Waypoint/route trace management: placement, undo, CSV export.
 */

import { onDraw, onCanvasClick, imageToScreen, draw } from './canvas.js';
import { fetchExport } from './api.js';
import { setStatus, markDirty } from './persistence.js';
import { getCoeffs } from './gcp.js';

let waypoints = [];

export function getWaypoints() { return waypoints; }
export function setWaypoints(list) { waypoints = list; }

// --- Click handler ---

onCanvasClick('trace', (pt) => {
  const idx = waypoints.length;
  const nameInput = document.getElementById('wp-name');
  const name = nameInput.value || `WP${String(idx + 1).padStart(3, '0')}`;
  waypoints.push({ px: Math.round(pt.x), py: Math.round(pt.y), name, idx });
  markDirty();
  // Auto-increment name
  const m = name.match(/^(.+?)(\d+)$/);
  if (m) {
    nameInput.value = m[1] + String(parseInt(m[2]) + 1).padStart(m[2].length, '0');
  }
  updateWPTable();
  setStatus(`Waypoint ${name} at pixel (${Math.round(pt.x)}, ${Math.round(pt.y)})`);
});

// --- Actions ---

export function undoWP() {
  if (waypoints.length) { waypoints.pop(); markDirty(); updateWPTable(); draw(); }
}

export async function exportCSV() {
  const { lon: coeffsLon, lat: coeffsLat } = getCoeffs();
  if (!coeffsLon || !coeffsLat) { setStatus('Compute transform first'); return; }
  if (!waypoints.length) { setStatus('No waypoints to export'); return; }
  const data = await fetchExport(coeffsLon, coeffsLat, waypoints);
  document.getElementById('csv-output').value = data.csv;
  setStatus(`Exported ${waypoints.length} waypoints`);
}

// --- Table ---

export function updateWPTable() {
  const tbody = document.querySelector('#wp-table tbody');
  tbody.innerHTML = '';
  for (let i = 0; i < waypoints.length; i++) {
    const w = waypoints[i];
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${i+1}</td><td>${w.name}</td><td>${w.px},${w.py}</td>`;
    tbody.appendChild(tr);
  }
}

// --- Draw hook ---

onDraw((ctx, scale, ox, oy) => {
  // Draw route line
  if (waypoints.length > 1) {
    ctx.beginPath();
    ctx.strokeStyle = 'rgba(50,150,255,0.7)';
    ctx.lineWidth = 2;
    const s0 = imageToScreen(waypoints[0].px, waypoints[0].py);
    ctx.moveTo(s0.x, s0.y);
    for (let i = 1; i < waypoints.length; i++) {
      const s = imageToScreen(waypoints[i].px, waypoints[i].py);
      ctx.lineTo(s.x, s.y);
    }
    ctx.stroke();
  }

  // Draw waypoint dots
  for (let i = 0; i < waypoints.length; i++) {
    const w = waypoints[i];
    const s = imageToScreen(w.px, w.py);
    ctx.beginPath();
    ctx.arc(s.x, s.y, 4, 0, Math.PI * 2);
    ctx.fillStyle = '#38f';
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1;
    ctx.stroke();
    if (w.name) {
      ctx.fillStyle = '#adf';
      ctx.font = '10px system-ui';
      ctx.fillText(w.name, s.x + 6, s.y - 3);
    }
  }
});
