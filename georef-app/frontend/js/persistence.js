/**
 * Save/load state, dirty tracking, status bar, keyboard shortcuts.
 */

import { fetchSave, fetchLoad } from './api.js';
import { draw } from './canvas.js';

let isDirty = false;
let lastSavedAt = null;

// These get wired up by app.js after all modules load
let _getState = null;
let _setState = null;
let _onSave = null;

export function initPersistence({ getState, setState, onSave }) {
  _getState = getState;
  _setState = setState;
  _onSave = onSave;
}

export function markDirty() {
  isDirty = true;
  updateSaveStatus();
}

export function setStatus(msg) {
  document.getElementById('status').textContent = msg;
}

function updateSaveStatus() {
  const el = document.getElementById('save-status');
  if (isDirty) {
    el.textContent = 'Unsaved changes';
    el.style.color = '#e44';
  } else if (lastSavedAt) {
    const d = new Date(lastSavedAt);
    el.textContent = `Last saved: ${d.toLocaleTimeString()}`;
    el.style.color = '#888';
  } else {
    el.textContent = '';
  }
}

export async function saveState() {
  if (!_getState) return;
  const { imgName, gcps, waypoints, coeffsLon, coeffsLat } = _getState();
  if (!imgName) return;
  const result = await fetchSave(imgName, gcps, waypoints, coeffsLon, coeffsLat);
  lastSavedAt = result.saved_at;
  isDirty = false;
  updateSaveStatus();
  setStatus('Saved');
}

export async function loadState() {
  if (!_getState || !_setState) return;
  const { imgName } = _getState();
  if (!imgName) return;
  const data = await fetchLoad(imgName);
  _setState(data);
  lastSavedAt = data.saved_at || null;
  isDirty = false;
  updateSaveStatus();
  draw();
  const gcpCount = (data.gcps || []).length;
  const wpCount = (data.waypoints || []).length;
  if (gcpCount) setStatus(`Loaded ${gcpCount} GCPs, ${wpCount} waypoints`);
}

export function getIsDirty() { return isDirty; }
export function getLastSavedAt() { return lastSavedAt; }

export function checkUnsavedChanges(imgName) {
  if (!isDirty) return true;
  let msg = `You have unsaved changes on "${imgName}".`;
  if (lastSavedAt) {
    msg += `\nLast saved: ${new Date(lastSavedAt).toLocaleString()}`;
  } else {
    msg += `\nThis image has never been saved.`;
  }
  msg += `\n\nSwitch and discard changes?`;
  return confirm(msg);
}
