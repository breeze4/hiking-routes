/**
 * App entry point: init, image loading, mode switching, keyboard shortcuts.
 */

import { fetchImages, imageUrl } from './api.js';
import { setImg, resetView, draw, setCurrentMode, onMouseMove } from './canvas.js';
import { commitGCP, undoGCP, computeTransform, getGCPs, getCoeffs, setGCPs, setCoeffs, updateGCPTable } from './gcp.js';
import { undoWP, exportCSV, getWaypoints, setWaypoints, updateWPTable } from './trace.js';
import { runAutoTrace } from './autotrace.js';
import { initPersistence, saveState, loadState, setStatus, checkUnsavedChanges } from './persistence.js';
import { init as initOverlay } from './overlay-app.js';

let imgName = '';
let mode = 'gcp';
let currentView = 'georef';

// --- Wire up persistence with state accessors ---

initPersistence({
  getState: () => ({
    imgName,
    gcps: getGCPs(),
    waypoints: getWaypoints(),
    coeffsLon: getCoeffs().lon,
    coeffsLat: getCoeffs().lat,
  }),
  setState: (data) => {
    const gcps = (data.gcps || []).map(g => ({ px: g.px, py: g.py, lon: g.lon, lat: g.lat }));
    const waypoints = (data.waypoints || []).map((w, i) => ({
      px: w.px, py: w.py, name: w.name || `WP${String(i+1).padStart(3,'0')}`, idx: i,
    }));
    setGCPs(gcps);
    setWaypoints(waypoints);
    setCoeffs(data.coeffs_lon || null, data.coeffs_lat || null);
    updateGCPTable();
    updateWPTable();
  },
});

// --- Image loading ---

async function loadImageList() {
  const images = await fetchImages();
  const sel = document.getElementById('image-select');
  for (const img of images) {
    const opt = document.createElement('option');
    opt.value = img.name;
    opt.textContent = img.label;
    sel.appendChild(opt);
  }
}

document.getElementById('image-select').addEventListener('change', (e) => {
  const name = e.target.value;
  if (!name) return;
  if (!checkUnsavedChanges(imgName)) {
    e.target.value = imgName;
    return;
  }
  imgName = name;
  const img = new Image();
  img.onload = () => {
    setImg(img);
    resetView();
    loadState();
  };
  img.src = imageUrl(name);
});

// --- Mode switching ---

function setMode(m) {
  mode = m;
  setCurrentMode(m);
  document.getElementById('btn-gcp').classList.toggle('active', m === 'gcp');
  document.getElementById('btn-trace').classList.toggle('active', m === 'trace');
  document.getElementById('gcp-section').style.display = m === 'gcp' ? '' : 'none';
  document.getElementById('trace-section').style.display = m === 'trace' ? '' : 'none';
}

document.getElementById('btn-gcp').addEventListener('click', () => setMode('gcp'));
document.getElementById('btn-trace').addEventListener('click', () => setMode('trace'));

// --- Button wiring ---

document.getElementById('btn-set-coords').addEventListener('click', commitGCP);
document.getElementById('btn-undo-gcp').addEventListener('click', undoGCP);
document.getElementById('btn-compute-transform').addEventListener('click', computeTransform);
document.getElementById('btn-undo-wp').addEventListener('click', undoWP);
document.getElementById('btn-export-csv').addEventListener('click', exportCSV);
document.getElementById('btn-autotrace').addEventListener('click', () => runAutoTrace(imgName));
document.getElementById('btn-save').addEventListener('click', saveState);
document.getElementById('btn-load').addEventListener('click', loadState);

// --- Mouse move status ---

onMouseMove((pt) => {
  let msg = `Pixel: (${Math.round(pt.x)}, ${Math.round(pt.y)})`;
  const { lon: coeffsLon, lat: coeffsLat } = getCoeffs();
  if (coeffsLon && coeffsLat) {
    const lon = coeffsLon[0] * pt.x + coeffsLon[1] * pt.y + coeffsLon[2];
    const lat = coeffsLat[0] * pt.x + coeffsLat[1] * pt.y + coeffsLat[2];
    msg += `  |  ${lat.toFixed(5)}, ${lon.toFixed(5)}`;
  }
  setStatus(msg);
});

// --- Keyboard shortcuts ---

document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
    if (e.key === 'Enter' && mode === 'gcp') { commitGCP(); e.preventDefault(); }
    return;
  }
  if (e.key === 'g') setMode('gcp');
  if (e.key === 't') setMode('trace');
  if (e.key === 'z' && e.ctrlKey) {
    if (mode === 'gcp') undoGCP(); else undoWP();
  }
  if (e.key === 's' && e.ctrlKey) { e.preventDefault(); saveState(); }
});

// --- View switching ---

function setView(view) {
  currentView = view;
  document.getElementById('btn-view-georef').classList.toggle('active', view === 'georef');
  document.getElementById('btn-view-overlay').classList.toggle('active', view === 'overlay');
  document.getElementById('georef-sidebar').style.display = view === 'georef' ? '' : 'none';
  document.getElementById('overlay-sidebar').style.display = view === 'overlay' ? '' : 'none';
  document.getElementById('canvas-wrap').style.display = view === 'georef' ? '' : 'none';
  document.getElementById('map-wrap').style.display = view === 'overlay' ? '' : 'none';

  if (view === 'overlay') initOverlay();
}

document.getElementById('btn-view-georef').addEventListener('click', () => setView('georef'));
document.getElementById('btn-view-overlay').addEventListener('click', () => setView('overlay'));

// --- Init ---
loadImageList();
