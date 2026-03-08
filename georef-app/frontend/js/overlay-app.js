/**
 * Overlay view: Leaflet map with visual image placement and point placement.
 * Lazily initialized — call init() when switching to overlay view.
 */

import { fetchOverlays, imageUrl, savePlacement } from './api.js';

let map = null;
let initialized = false;
let placingPoints = false;
let points = [];
let pointCounter = 1;

// Each entry: { name, label, width, height, layer, handles, opacity, el, pin, locked }
// pin: null or { geo: {lat,lng}, frac: {x,y}, marker, scaleBase: {w,h} }
const images = [];
let pinningEntry = null; // entry currently waiting for a pin click

// --- Init ---

export function init() {
  if (initialized) {
    setTimeout(() => map.invalidateSize(), 0);
    return;
  }
  initialized = true;

  map = L.map('map', { zoomControl: true }).setView([37.41, -111.04], 13);
  L.tileLayer(
    'https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}',
    { maxZoom: 16, attribution: 'USGS' }
  ).addTo(map);

  map.on('click', onMapClick);
  wireUI();
  loadImages();
}

// --- Image list ---

async function loadImages() {
  const data = await fetchOverlays();
  const listEl = document.getElementById('image-list');
  const placedBounds = [];

  for (const item of data) {
    const entry = {
      name: item.image_name,
      label: item.label,
      width: item.width,
      height: item.height,
      layer: null,
      handles: null,
      opacity: 0.7,
      el: null,
      pin: null,
      locked: false,
    };
    images.push(entry);

    const div = document.createElement('div');
    div.className = 'image-item';
    entry.el = div;

    if (item.placed) {
      const bounds = item.bounds || computeBoundsFromAffine(item);
      addToMap(entry, bounds);
      placedBounds.push(bounds);
      renderPlacedControls(entry);
    } else {
      renderUnplacedControls(entry);
    }

    listEl.appendChild(div);
  }

  if (placedBounds.length) {
    const allLats = placedBounds.flatMap(b => [b[0][0], b[1][0]]);
    const allLons = placedBounds.flatMap(b => [b[0][1], b[1][1]]);
    map.fitBounds([
      [Math.min(...allLats), Math.min(...allLons)],
      [Math.max(...allLats), Math.max(...allLons)]
    ]);
  }
}

function computeBoundsFromAffine(item) {
  const { coeffs_lon: cl, coeffs_lat: ca, width: w, height: h } = item;
  const corners = [[0, 0], [w, 0], [w, h], [0, h]].map(([px, py]) => [
    ca[0] * px + ca[1] * py + ca[2],
    cl[0] * px + cl[1] * py + cl[2],
  ]);
  const lats = corners.map(c => c[0]);
  const lons = corners.map(c => c[1]);
  return [[Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]];
}

// --- Sidebar controls ---

function renderUnplacedControls(entry) {
  const div = entry.el;
  div.innerHTML = '';

  const label = document.createElement('span');
  label.className = 'image-label';
  label.textContent = entry.label;
  label.title = entry.name;

  const btn = document.createElement('button');
  btn.textContent = 'Add to map';
  btn.addEventListener('click', () => {
    const viewBounds = map.getBounds();
    const center = viewBounds.getCenter();
    const viewH = viewBounds.getNorth() - viewBounds.getSouth();
    const viewW = viewBounds.getEast() - viewBounds.getWest();

    // Size to ~1/3 of viewport, maintaining image aspect ratio
    const aspect = entry.width / entry.height;
    let h = viewH * 0.33;
    let w = h * aspect;
    if (w > viewW * 0.33) {
      w = viewW * 0.33;
      h = w / aspect;
    }

    const bounds = [
      [center.lat - h / 2, center.lng - w / 2],
      [center.lat + h / 2, center.lng + w / 2],
    ];
    addToMap(entry, bounds);
    renderPlacedControls(entry);
  });

  div.append(label, btn);
}

function renderPlacedControls(entry) {
  const div = entry.el;
  div.innerHTML = '';

  const label = document.createElement('span');
  label.className = 'image-label';
  label.textContent = entry.label;
  label.title = entry.name;

  // Row 1: visibility, opacity, pin
  const controls = document.createElement('div');
  controls.className = 'image-controls';

  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.checked = true;
  cb.addEventListener('change', () => {
    entry.layer.setOpacity(cb.checked ? entry.opacity : 0);
    if (!entry.pin) setHandlesVisible(entry, cb.checked);
  });

  const opacitySlider = document.createElement('input');
  opacitySlider.type = 'range';
  opacitySlider.min = '0'; opacitySlider.max = '1'; opacitySlider.step = '0.05';
  opacitySlider.value = String(entry.opacity);
  opacitySlider.addEventListener('input', () => {
    entry.opacity = parseFloat(opacitySlider.value);
    if (cb.checked) entry.layer.setOpacity(entry.opacity);
  });

  const pinBtn = document.createElement('button');
  if (entry.pin) {
    pinBtn.textContent = 'Unpin';
    pinBtn.addEventListener('click', () => {
      clearPin(entry);
      renderPlacedControls(entry);
    });
  } else if (pinningEntry === entry) {
    pinBtn.textContent = 'Pin...';
    pinBtn.classList.add('active');
    pinBtn.addEventListener('click', () => {
      pinningEntry = null;
      map.getContainer().style.cursor = '';
      renderPlacedControls(entry);
    });
  } else {
    pinBtn.textContent = 'Pin';
    pinBtn.title = 'Click map to set anchor point for scaling';
    pinBtn.addEventListener('click', () => {
      pinningEntry = entry;
      map.getContainer().style.cursor = 'crosshair';
      renderPlacedControls(entry);
    });
  }

  const lockBtn = document.createElement('button');
  lockBtn.textContent = entry.locked ? 'Unlock' : 'Lock';
  lockBtn.addEventListener('click', () => {
    setLocked(entry, !entry.locked);
    renderPlacedControls(entry);
  });

  controls.append(cb, opacitySlider);
  if (!entry.locked) controls.append(pinBtn);
  controls.append(lockBtn);

  // Row 2: save, remove
  const actionRow = document.createElement('div');
  actionRow.className = 'image-controls';

  const saveBtn = document.createElement('button');
  saveBtn.textContent = 'Save';
  saveBtn.addEventListener('click', () => saveImage(entry, statusEl));

  const removeBtn = document.createElement('button');
  removeBtn.textContent = 'Remove';
  removeBtn.addEventListener('click', () => {
    clearPin(entry);
    removeFromMap(entry);
    renderUnplacedControls(entry);
  });

  const statusEl = document.createElement('div');
  statusEl.className = 'save-status';

  actionRow.append(saveBtn, removeBtn);
  div.append(label, controls, actionRow, statusEl);
}

// --- Map overlay + handles ---

function addToMap(entry, bounds) {
  const layer = L.imageOverlay(imageUrl(entry.name), bounds, { opacity: entry.opacity });
  layer.addTo(map);
  entry.layer = layer;

  function makeCorner(latLng) {
    return L.marker(latLng, {
      draggable: true,
      icon: L.divIcon({ className: 'handle-corner', iconSize: [12, 12], iconAnchor: [6, 6] }),
    }).addTo(map);
  }

  // corners: [SW, NW, NE, SE]
  const sw = makeCorner(bounds[0]);
  const nw = makeCorner([bounds[1][0], bounds[0][1]]);
  const ne = makeCorner(bounds[1]);
  const se = makeCorner([bounds[0][0], bounds[1][1]]);
  const corners = [sw, nw, ne, se];

  const centerLL = [(bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2];
  const center = L.marker(centerLL, {
    draggable: true,
    icon: L.divIcon({ className: 'handle-center', iconSize: [14, 14], iconAnchor: [7, 7] }),
  }).addTo(map);

  function syncFromBounds(south, west, north, east) {
    layer.setBounds([[south, west], [north, east]]);
    sw.setLatLng([south, west]);
    nw.setLatLng([north, west]);
    ne.setLatLng([north, east]);
    se.setLatLng([south, east]);
    center.setLatLng([(south + north) / 2, (west + east) / 2]);
  }

  // Corner drag: if pin is set, scale uniformly around pin; otherwise resize freely
  function pinScale(draggedCorner) {
    const pin = entry.pin;
    const p = draggedCorner.getLatLng();
    // Distance from pin to dragged corner position
    const dLat = p.lat - pin.geo.lat;
    const dLng = p.lng - pin.geo.lng;
    const dist = Math.sqrt(dLat * dLat + dLng * dLng);

    // Original distance from pin to the same corner at scale=1
    const b = pin.scaleBase;
    // Figure out which corner this is to get its fractional offset from pin
    const idx = corners.indexOf(draggedCorner);
    // Corner fracs: SW(0,0) NW(0,1) NE(1,1) SE(1,0)
    const cornerFracs = [[0, 0], [0, 1], [1, 1], [1, 0]];
    const cf = cornerFracs[idx];
    const origDLng = (cf[0] - pin.frac.x) * b.w;
    const origDLat = (cf[1] - pin.frac.y) * b.h;
    const origDist = Math.sqrt(origDLat * origDLat + origDLng * origDLng);

    if (origDist < 1e-10) return;
    const scale = dist / origDist;
    scaleAroundPin(entry, scale);
  }

  sw.on('drag', () => {
    if (entry.pin) { pinScale(sw); return; }
    const p = sw.getLatLng(), o = ne.getLatLng();
    syncFromBounds(p.lat, p.lng, o.lat, o.lng);
  });
  ne.on('drag', () => {
    if (entry.pin) { pinScale(ne); return; }
    const p = ne.getLatLng(), o = sw.getLatLng();
    syncFromBounds(o.lat, o.lng, p.lat, p.lng);
  });
  nw.on('drag', () => {
    if (entry.pin) { pinScale(nw); return; }
    const p = nw.getLatLng(), o = se.getLatLng();
    syncFromBounds(o.lat, p.lng, p.lat, o.lng);
  });
  se.on('drag', () => {
    if (entry.pin) { pinScale(se); return; }
    const p = se.getLatLng(), o = nw.getLatLng();
    syncFromBounds(p.lat, o.lng, o.lat, p.lng);
  });

  // Center drag: move entire overlay (and pin if set)
  let prevCenter = L.latLng(centerLL[0], centerLL[1]);
  center.on('dragstart', () => {
    prevCenter = center.getLatLng();
  });
  center.on('drag', () => {
    const curr = center.getLatLng();
    const dLat = curr.lat - prevCenter.lat;
    const dLng = curr.lng - prevCenter.lng;
    prevCenter = curr;

    const b = layer.getBounds();
    syncFromBounds(b.getSouth() + dLat, b.getWest() + dLng, b.getNorth() + dLat, b.getEast() + dLng);

    // Move pin with the overlay
    if (entry.pin) {
      entry.pin.geo.lat += dLat;
      entry.pin.geo.lng += dLng;
      entry.pin.marker.setLatLng([entry.pin.geo.lat, entry.pin.geo.lng]);
    }
  });

  entry.handles = { corners, center };
}

function removeFromMap(entry) {
  if (entry.layer) { map.removeLayer(entry.layer); entry.layer = null; }
  if (entry.handles) {
    entry.handles.corners.forEach(c => map.removeLayer(c));
    map.removeLayer(entry.handles.center);
    entry.handles = null;
  }
}

function setHandlesVisible(entry, visible) {
  if (!entry.handles) return;
  const op = visible ? 1 : 0;
  entry.handles.corners.forEach(c => { c.getElement().style.opacity = op; });
  entry.handles.center.getElement().style.opacity = op;
}

function setLocked(entry, locked) {
  entry.locked = locked;
  if (!entry.handles) return;
  entry.handles.corners.forEach(c => {
    if (locked) c.dragging.disable(); else c.dragging.enable();
    c.getElement().style.display = locked ? 'none' : '';
  });
  if (locked) entry.handles.center.dragging.disable(); else entry.handles.center.dragging.enable();
  entry.handles.center.getElement().style.display = locked ? 'none' : '';
  // Also hide pin marker when locked
  if (entry.pin) {
    entry.pin.marker.getElement().style.display = locked ? 'none' : '';
  }
}

// --- Save ---

async function saveImage(entry, statusEl) {
  const b = entry.layer.getBounds();
  const bounds = [[b.getSouth(), b.getWest()], [b.getNorth(), b.getEast()]];
  const w = entry.width, h = entry.height;
  const coeffsLon = [(bounds[1][1] - bounds[0][1]) / w, 0, bounds[0][1]];
  const coeffsLat = [0, (bounds[0][0] - bounds[1][0]) / h, bounds[1][0]];

  const result = await savePlacement(entry.name, coeffsLon, coeffsLat, bounds);
  if (result.ok) {
    statusEl.textContent = 'Saved';
    setTimeout(() => { statusEl.textContent = ''; }, 2000);
  }
}

// --- Pin for scale ---

function setPin(entry, latlng) {
  const b = entry.layer.getBounds();
  const south = b.getSouth(), west = b.getWest(), north = b.getNorth(), east = b.getEast();

  // Fractional position of pin within bounds (0..1)
  const frac = {
    x: (latlng.lng - west) / (east - west),
    y: (latlng.lat - south) / (north - south),
  };

  // Current geo-size as the scale=1 baseline
  const scaleBase = { w: east - west, h: north - south };

  const marker = L.marker(latlng, {
    icon: L.divIcon({ className: 'handle-pin', iconSize: [16, 16], iconAnchor: [8, 8] }),
    interactive: false,
  }).addTo(map);

  entry.pin = { geo: { lat: latlng.lat, lng: latlng.lng }, frac, marker, scaleBase };
}

function clearPin(entry) {
  if (!entry.pin) return;
  map.removeLayer(entry.pin.marker);
  entry.pin = null;
}

function scaleAroundPin(entry, scaleFactor) {
  const pin = entry.pin;
  if (!pin) return;

  const newW = pin.scaleBase.w * scaleFactor;
  const newH = pin.scaleBase.h * scaleFactor;

  const west = pin.geo.lng - pin.frac.x * newW;
  const east = pin.geo.lng + (1 - pin.frac.x) * newW;
  const south = pin.geo.lat - pin.frac.y * newH;
  const north = pin.geo.lat + (1 - pin.frac.y) * newH;

  entry.layer.setBounds([[south, west], [north, east]]);
  syncHandles(entry, south, west, north, east);
}

function syncHandles(entry, south, west, north, east) {
  const h = entry.handles;
  if (!h) return;
  h.corners[0].setLatLng([south, west]);  // SW
  h.corners[1].setLatLng([north, west]);  // NW
  h.corners[2].setLatLng([north, east]);  // NE
  h.corners[3].setLatLng([south, east]);  // SE
  h.center.setLatLng([(south + north) / 2, (west + east) / 2]);
}

// --- Point placement ---

function onMapClick(e) {
  // Pin placement takes priority
  if (pinningEntry) {
    setPin(pinningEntry, e.latlng);
    renderPlacedControls(pinningEntry);
    pinningEntry = null;
    map.getContainer().style.cursor = '';
    return;
  }

  if (!placingPoints) return;

  const defaultName = `PT${String(pointCounter).padStart(3, '0')}`;
  const name = prompt('Point label:', defaultName);
  if (name === null) return;

  const { lat, lng: lon } = e.latlng;
  const marker = L.marker([lat, lon]).addTo(map);
  marker.bindPopup(`<b>${name}</b><br>${lat.toFixed(5)}, ${lon.toFixed(5)}`);

  points.push({ name, lat, lon, marker });
  pointCounter++;
  renderPointsTable();
}

function removePoint(idx) {
  map.removeLayer(points[idx].marker);
  points.splice(idx, 1);
  renderPointsTable();
}

function undoPoint() {
  if (points.length) removePoint(points.length - 1);
}

function renderPointsTable() {
  const tbody = document.querySelector('#points-table tbody');
  tbody.innerHTML = '';
  points.forEach((pt, i) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td>${pt.name}</td>
      <td>${pt.lat.toFixed(5)}</td>
      <td>${pt.lon.toFixed(5)}</td>
      <td><button class="del-btn">&times;</button></td>
    `;
    tr.querySelector('button').addEventListener('click', () => removePoint(i));
    tbody.appendChild(tr);
  });
}

function exportCSV() {
  if (!points.length) return;
  const lines = ['name,lat,lon'];
  for (const pt of points) {
    lines.push(`${pt.name},${pt.lat.toFixed(5)},${pt.lon.toFixed(5)}`);
  }
  document.getElementById('points-csv-output').value = lines.join('\n');
}

async function copyCSV() {
  const text = document.getElementById('points-csv-output').value;
  if (text) await navigator.clipboard.writeText(text);
}

// --- UI wiring ---

function wireUI() {
  const btnPlace = document.getElementById('btn-place');
  btnPlace.addEventListener('click', () => {
    placingPoints = !placingPoints;
    btnPlace.classList.toggle('active', placingPoints);
    map.getContainer().style.cursor = placingPoints ? 'crosshair' : '';
  });

  document.getElementById('btn-undo-point').addEventListener('click', undoPoint);
  document.getElementById('btn-export-points').addEventListener('click', exportCSV);
  document.getElementById('btn-copy-points').addEventListener('click', copyCSV);
}
