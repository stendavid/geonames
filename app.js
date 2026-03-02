// ── GeoNames Suffix Search — Application Logic ─────────────────────

// ── Shared state ────────────────────────────────────────────────────
const cache = {};           // country code → array of place objects
let markerLayer = null;     // current LayerGroup of circle markers on the map

// ── Map initialisation ─────────────────────────────────────────────
const map = L.map("map").setView([54, 10], 4); // Center on northern Europe

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

// ── Global data registry (populated by data/*.js script tags) ───────
window.__geodata = window.__geodata || {};

// ── Data loading (script-tag injection + cached) ────────────────────

/**
 * Load the data for a country code.  Returns the cached array if
 * already loaded, otherwise injects a <script> tag for data/<code>.js
 * which registers its payload on window.__geodata[code].
 *
 * This approach works from file:// — no HTTP server required.
 */
function loadCountryData(code) {
  if (cache[code]) {
    return Promise.resolve(cache[code]);
  }

  // Check if the data was already registered (e.g. by a static script tag)
  if (window.__geodata[code]) {
    cache[code] = window.__geodata[code];
    return Promise.resolve(cache[code]);
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `data/${code}.js`;
    script.onload = () => {
      if (window.__geodata[code]) {
        cache[code] = window.__geodata[code];
        resolve(cache[code]);
      } else {
        reject(new Error(`data/${code}.js loaded but did not register data`));
      }
    };
    script.onerror = () =>
      reject(new Error(`Failed to load data/${code}.js`));
    document.head.appendChild(script);
  });
}

// ── Filtering helpers ───────────────────────────────────────────────

/**
 * Return places whose name ends with the given suffix.
 * Both the suffix and the name are compared in lower-case.
 * An empty / whitespace-only suffix returns an empty array.
 */
function filterBySuffix(places, suffix) {
  const s = suffix.trim().toLowerCase();
  if (s.length === 0) return [];
  return places.filter((p) => p.name.toLowerCase().endsWith(s));
}

/**
 * Return places whose population is ≥ minPop.
 */
function filterByPopulation(places, minPop) {
  return places.filter((p) => p.population >= minPop);
}

// ── UI helpers ──────────────────────────────────────────────────────

function getSelectedCountries() {
  return Array.from(
    document.querySelectorAll('#country-selector input[name="country"]:checked')
  ).map((cb) => cb.value);
}

function getSuffix() {
  return document.getElementById("suffix-input").value;
}

function getMinPopulation() {
  const val = parseInt(document.getElementById("population-input").value, 10);
  return Number.isNaN(val) ? 0 : val;
}

function setResultCount(n) {
  const el = document.getElementById("result-count");
  el.textContent = n === 0 ? "No results" : `${n} result${n !== 1 ? "s" : ""}`;
}

// ── Map plotting ────────────────────────────────────────────────────

const DOT_STYLE = {
  radius: 4,
  weight: 0.5,
  color: "#1a5276",
  fillColor: "#2e86c1",
  fillOpacity: 0.7,
};

/**
 * Clear existing markers and plot the given places as small circle
 * dots on the map.
 */
function plotMarkers(places) {
  // Remove previous layer
  if (markerLayer) {
    map.removeLayer(markerLayer);
  }

  markerLayer = L.layerGroup();

  places.forEach((p) => {
    const dot = L.circleMarker([p.lat, p.lon], DOT_STYLE);
    dot.bindTooltip(
      `<strong>${p.name}</strong><br/>Pop. ${p.population.toLocaleString()}`,
      { direction: "top", offset: [0, -6] }
    );
    markerLayer.addLayer(dot);
  });

  map.addLayer(markerLayer);

  // Fit map bounds to results (if any)
  if (places.length > 0) {
    const bounds = L.featureGroup(markerLayer.getLayers()).getBounds();
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 10 });
  }
}

// ── Main search routine ─────────────────────────────────────────────

async function search() {
  const countries = getSelectedCountries();
  const suffix = getSuffix();
  const minPop = getMinPopulation();

  // Nothing selected or no suffix → clear map
  if (countries.length === 0 || suffix.trim().length === 0) {
    plotMarkers([]);
    setResultCount(0);
    return;
  }

  // Load all selected country data in parallel
  const datasets = await Promise.all(countries.map(loadCountryData));

  // Merge, filter by suffix, then by population
  const merged = datasets.flat();
  const bySuffix = filterBySuffix(merged, suffix);
  const results = filterByPopulation(bySuffix, minPop);

  plotMarkers(results);
  setResultCount(results.length);
}

// ── Debounce helper ─────────────────────────────────────────────────

function debounce(fn, ms) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), ms);
  };
}

// ── Event wiring ────────────────────────────────────────────────────

const debouncedSearch = debounce(search, 300);

document.getElementById("suffix-input").addEventListener("input", debouncedSearch);
document.getElementById("population-input").addEventListener("input", debouncedSearch);
document
  .querySelectorAll('#country-selector input[name="country"]')
  .forEach((cb) => cb.addEventListener("change", search));

// ── Expose internals for browser-based tests ────────────────────────
const App = {
  cache,
  loadCountryData,
  filterBySuffix,
  filterByPopulation,
  getSelectedCountries,
  getSuffix,
  getMinPopulation,
  setResultCount,
  plotMarkers,
  search,
};
