/**
 * GCP (Ground Control Point) management: placement, commit, undo, transform.
 */

import { onDraw, onCanvasClick, imageToScreen, draw } from './canvas.js';
import { fetchTransform } from './api.js';
import { setStatus, markDirty } from './persistence.js';

let gcps = [];
let pendingGCP = null;
let coeffsLon = null;
let coeffsLat = null;

export function getGCPs() { return gcps; }
export function getCoeffs() { return { lon: coeffsLon, lat: coeffsLat }; }

export function setGCPs(list) { gcps = list; }
export function setCoeffs(lon, lat) { coeffsLon = lon; coeffsLat = lat; }

// --- Click handler ---

onCanvasClick('gcp', (pt) => {
  pendingGCP = { px: Math.round(pt.x), py: Math.round(pt.y) };
  document.getElementById('gcp-coords').focus();
  setStatus(`GCP placed at pixel (${pendingGCP.px}, ${pendingGCP.py}) - enter lat/lon and click Set Coords`);
});

// --- Actions ---

export function commitGCP() {
  if (!pendingGCP) { setStatus('Click on the map first to place a GCP'); return; }
  const raw = document.getElementById('gcp-coords').value.trim();
  const parts = raw.split(/[\s,]+/).filter(Boolean);
  if (parts.length !== 2) { setStatus('Enter coords as: 37.41907, -111.04314'); return; }
  const lat = parseFloat(parts[0]);
  const lon = parseFloat(parts[1]);
  if (isNaN(lat) || isNaN(lon)) { setStatus('Enter coords as: 37.41907, -111.04314'); return; }
  gcps.push({ ...pendingGCP, lat, lon });
  pendingGCP = null;
  document.getElementById('gcp-coords').value = '';
  markDirty();
  updateGCPTable();
  draw();
  setStatus(`GCP ${gcps.length} set at (${lat.toFixed(5)}, ${lon.toFixed(5)})`);
}

export function undoGCP() {
  if (pendingGCP) { pendingGCP = null; }
  else if (gcps.length) { gcps.pop(); markDirty(); }
  updateGCPTable();
  draw();
}

export async function computeTransform() {
  if (gcps.length < 3) { setStatus('Need at least 3 GCPs'); return; }
  const data = await fetchTransform(gcps);
  if (data.error) { setStatus(`Error: ${data.error}`); return; }

  coeffsLon = data.coeffs_lon;
  coeffsLat = data.coeffs_lat;
  markDirty();

  for (const r of data.residuals) {
    gcps[r.idx]._errMeters = r.err_meters;
    gcps[r.idx]._errClass = r.err_meters < 100 ? 'err-ok' : 'err-bad';
  }
  updateGCPTable();
  draw();

  const maxErr = Math.max(...data.residuals.map(r => r.err_meters));
  setStatus(`Transform computed. Max residual: ${maxErr.toFixed(1)}m`);
}

// --- Table ---

export function updateGCPTable() {
  const tbody = document.querySelector('#gcp-table tbody');
  tbody.innerHTML = '';
  for (let i = 0; i < gcps.length; i++) {
    const g = gcps[i];
    const tr = document.createElement('tr');
    const errClass = g._errClass || '';
    const errText = g._errMeters != null ? `${g._errMeters}m` : '-';
    tr.innerHTML = `<td>${i+1}</td><td>${g.px},${g.py}</td><td>${g.lat.toFixed(5)}, ${g.lon.toFixed(5)}</td><td class="${errClass}">${errText}</td>`;
    tbody.appendChild(tr);
  }
}

// --- Draw hook ---

onDraw((ctx, scale, ox, oy) => {
  // Draw GCPs
  for (let i = 0; i < gcps.length; i++) {
    const g = gcps[i];
    const s = imageToScreen(g.px, g.py);
    ctx.beginPath();
    ctx.arc(s.x, s.y, 6, 0, Math.PI * 2);
    ctx.fillStyle = g._errClass === 'err-bad' ? '#e44' : '#e22';
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 10px system-ui';
    ctx.fillText(String(i + 1), s.x + 8, s.y - 4);
  }

  // Draw pending GCP
  if (pendingGCP) {
    const s = imageToScreen(pendingGCP.px, pendingGCP.py);
    ctx.beginPath();
    ctx.arc(s.x, s.y, 6, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(255,200,0,0.7)';
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
});
