/**
 * Centralized API fetch wrappers. All endpoint URLs live here.
 */

export async function fetchImages() {
  const res = await fetch('/api/images');
  return res.json();
}

export function imageUrl(name) {
  return `/api/image/${name}`;
}

export async function fetchTransform(gcps) {
  const res = await fetch('/api/transform', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ gcps }),
  });
  return res.json();
}

export async function fetchExport(coeffsLon, coeffsLat, waypoints) {
  const res = await fetch('/api/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ coeffs_lon: coeffsLon, coeffs_lat: coeffsLat, waypoints }),
  });
  return res.json();
}

export async function fetchSave(imageName, gcps, waypoints, coeffsLon, coeffsLat) {
  const res = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_name: imageName,
      gcps: gcps.map(g => ({ px: g.px, py: g.py, lon: g.lon, lat: g.lat })),
      waypoints: waypoints.map(w => ({ px: w.px, py: w.py, name: w.name })),
      coeffs_lon: coeffsLon,
      coeffs_lat: coeffsLat,
    }),
  });
  return res.json();
}

export async function fetchLoad(imageName) {
  const res = await fetch(`/api/load/${imageName}`);
  return res.json();
}

export async function savePlacement(imageName, coeffsLon, coeffsLat, bounds) {
  const res = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_name: imageName,
      coeffs_lon: coeffsLon,
      coeffs_lat: coeffsLat,
      bounds,
    }),
  });
  return res.json();
}

export async function fetchOverlays() {
  const res = await fetch('/api/overlays');
  return res.json();
}

export async function fetchAutoTrace(body) {
  const res = await fetch('/api/autotrace', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}
