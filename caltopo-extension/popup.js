(async function () {
  const statusEl = document.getElementById("map-status");
  const csvEl = document.getElementById("csv");
  const btnEl = document.getElementById("add-btn");
  const resultsEl = document.getElementById("results");

  // --- Map ID detection ---

  function extractMapId(url) {
    const match = url.match(/caltopo\.com\/(?:m|map)\/([A-Za-z0-9]+)/);
    return match ? match[1] : null;
  }

  let mapId = null;

  try {
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });
    if (tab && tab.url) {
      mapId = extractMapId(tab.url);
    }
  } catch (e) {
    // tabs query failed
  }

  if (mapId) {
    statusEl.textContent = "Map: " + mapId;
    statusEl.className = "ok";
    btnEl.disabled = false;
  } else {
    statusEl.textContent = "Not on a CalTopo map page";
    statusEl.className = "error";
    return;
  }

  // --- CSV parsing ---

  function parseCsv(text) {
    const lines = text.trim().split("\n");
    const markers = [];
    const errors = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      const parts = line.split(",").map((s) => s.trim());
      if (parts.length < 3) {
        errors.push("Line " + (i + 1) + ": need name,lat,lon");
        continue;
      }

      const name = parts[0];
      const lat = parseFloat(parts[1]);
      const lon = parseFloat(parts[2]);

      if (!name) {
        errors.push("Line " + (i + 1) + ": empty name");
        continue;
      }
      if (isNaN(lat) || lat < -90 || lat > 90) {
        errors.push("Line " + (i + 1) + ': invalid latitude "' + parts[1] + '"');
        continue;
      }
      if (isNaN(lon) || lon < -180 || lon > 180) {
        errors.push("Line " + (i + 1) + ': invalid longitude "' + parts[2] + '"');
        continue;
      }

      markers.push({ name, lat, lon });
    }

    return { markers, errors };
  }

  // --- API calls ---

  async function addMarker(name, lat, lon) {
    const feature = {
      type: "Feature",
      id: null,
      geometry: {
        type: "Point",
        coordinates: [lon, lat],
      },
      properties: {
        title: name,
        description: "",
        folderId: null,
        "marker-size": "1",
        "marker-symbol": "point",
        "marker-color": "FF0000",
        "marker-rotation": null,
      },
    };

    const resp = await fetch(
      "https://caltopo.com/api/v1/map/" + mapId + "/Marker",
      {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: "json=" + encodeURIComponent(JSON.stringify(feature)),
      }
    );

    if (!resp.ok) {
      const text = await resp.text();
      throw new Error(resp.status + ": " + text.slice(0, 200));
    }

    return await resp.json();
  }

  // --- UI wiring ---

  btnEl.addEventListener("click", async function () {
    resultsEl.innerHTML = "";
    const { markers, errors } = parseCsv(csvEl.value);

    for (const err of errors) {
      const div = document.createElement("div");
      div.className = "fail";
      div.textContent = err;
      resultsEl.appendChild(div);
    }

    if (markers.length === 0) {
      if (errors.length === 0) {
        const div = document.createElement("div");
        div.className = "fail";
        div.textContent = "No markers to add. Paste CSV as: name,lat,lon";
        resultsEl.appendChild(div);
      }
      return;
    }

    btnEl.disabled = true;
    btnEl.textContent = "Adding...";

    for (const m of markers) {
      const div = document.createElement("div");
      try {
        await addMarker(m.name, m.lat, m.lon);
        div.className = "success";
        div.textContent = m.name + " — added";
      } catch (e) {
        div.className = "fail";
        div.textContent = m.name + " — failed: " + e.message;
      }
      resultsEl.appendChild(div);
    }

    btnEl.disabled = false;
    btnEl.textContent = "Add Markers";
  });
})();
