// ── GeoNames Suffix Search — Application Logic ─────────────────────

// ── Shared state ────────────────────────────────────────────────────
const cache = {};           // country code → array of place objects
let markerLayer = null;     // current LayerGroup of circle markers on the map

// ── Dynamic suffix inputs ───────────────────────────────────────────
const COLOR_PALETTE = [
  { color: '#2e86c1', border: '#1a5276' },  // Blue
  { color: '#e74c3c', border: '#922b21' },  // Red
  { color: '#27ae60', border: '#186a3b' },  // Green
  { color: '#f39c12', border: '#d68910' },  // Orange
  { color: '#9b59b6', border: '#6c3483' },  // Purple
  { color: '#1abc9c', border: '#117a65' },  // Turquoise
  { color: '#e67e22', border: '#a04000' },  // Dark Orange
  { color: '#3498db', border: '#21618c' },  // Light Blue
  { color: '#e91e63', border: '#880e4f' },  // Pink
  { color: '#00bcd4', border: '#006064' },  // Cyan
];

let suffixInputs = [];  // Array of {id, color, element}
let nextInputId = 1;

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

// ── Dynamic suffix input management ─────────────────────────────────

/**
 * Create a new suffix input box with a color swatch and remove button.
 */
function createSuffixInput() {
  const id = nextInputId++;
  const colorIndex = (suffixInputs.length) % COLOR_PALETTE.length;
  const colors = COLOR_PALETTE[colorIndex];
  
  const container = document.createElement('div');
  container.className = 'suffix-input-group';
  container.dataset.inputId = id;
  
  const row = document.createElement('div');
  row.className = 'suffix-row';
  
  const swatch = document.createElement('span');
  swatch.className = 'suffix-swatch';
  swatch.style.background = colors.color;
  
  const input = document.createElement('input');
  input.type = 'text';
  input.id = `suffix-input-${id}`;
  input.className = 'suffix-input';
  input.placeholder = 'e.g. -by, -ville, -burg';
  input.autocomplete = 'off';
  input.addEventListener('input', debounce(search, 300));
  
  const removeBtn = document.createElement('button');
  removeBtn.className = 'remove-suffix-btn';
  removeBtn.innerHTML = '×';
  removeBtn.title = 'Remove this search box';
  removeBtn.onclick = () => removeSuffixInput(id);
  
  row.appendChild(input);
  row.appendChild(swatch);
  row.appendChild(removeBtn);
  
  container.appendChild(row);
  
  const inputData = { id, colors, element: container, input };
  suffixInputs.push(inputData);
  
  const inputsContainer = document.getElementById('suffix-inputs-container');
  inputsContainer.appendChild(container);
  
  return inputData;
}

/**
 * Remove a suffix input box by ID.
 */
function removeSuffixInput(id) {
  const index = suffixInputs.findIndex(item => item.id === id);
  if (index === -1) return;
  
  // Don't allow removing the last input box
  if (suffixInputs.length === 1) return;
  
  const inputData = suffixInputs[index];
  inputData.element.remove();
  suffixInputs.splice(index, 1);
  
  search();
}

/**
 * Initialize suffix inputs with the default two boxes.
 */
function initializeSuffixInputs() {
  createSuffixInput();
  createSuffixInput();
}

// ── Filtering helpers ───────────────────────────────────────────────

/**
 * Return places whose name ends with the given suffix pattern.
 * The suffix is treated as a regex pattern and matched case-insensitively.
 * A '$' anchor is automatically added if not present to ensure suffix matching.
 * An empty / whitespace-only suffix returns an empty array.
 */
function filterBySuffix(places, suffix) {
  const s = suffix.trim();
  if (s.length === 0) return [];
  
  try {
    // Ensure the pattern matches at the end (suffix)
    // Wrap pattern in non-capturing group to handle alternation correctly
    const pattern = s.endsWith('$') ? s : `(?:${s})$`;
    const regex = new RegExp(pattern, 'i'); // case-insensitive
    
    return places.filter((p) => regex.test(p.name));
  } catch (error) {
    // If regex is invalid, return empty array
    console.error('Invalid regex pattern:', error);
    return [];
  }
}

/**
 * Return places whose population is ≥ minPop.
 */
function filterByPopulation(places, minPop) {
  return places.filter((p) => p.population >= minPop);
}

// ── UI helpers ──────────────────────────────────────────────────────

function getSelectedCountries() {
  const val = document.getElementById("country-select").value;
  return val ? [val] : [];
}

function getAllSuffixes() {
  return suffixInputs.map(item => ({
    value: item.input.value,
    colors: item.colors
  }));
}

function getMinPopulation() {
  const val = parseInt(document.getElementById("population-input").value, 10);
  return Number.isNaN(val) ? 0 : val;
}

function getMinPlaces() {
  const val = parseInt(document.getElementById("min-places-input").value, 10);
  return Number.isNaN(val) || val < 1 ? 100 : val;
}

function setResultCount(n) {
  const el = document.getElementById("result-count");
  el.textContent = n === 0 ? "No results" : `${n} result${n !== 1 ? "s" : ""}`;
}

// ── Map plotting ────────────────────────────────────────────────────

/**
 * Generate a marker style for a given color.
 */
function createMarkerStyle(colors) {
  return {
    radius: 4,
    weight: 0.5,
    color: colors.border,
    fillColor: colors.color,
    fillOpacity: 0.7,
  };
}

const DOT_STYLE_FADED = {
  radius: 3,
  weight: 0.5,
  color: "#999",
  fillColor: "#ccc",
  fillOpacity: 0.3,
};

const DOT_STYLE_HIGHLIGHT = {
  radius: 5,
  weight: 0.5,
  color: "#d68910",
  fillColor: "#f39c12",
  fillOpacity: 0.85,
};

// Track current highlight state
let currentHighlight = {
  active: false,
  suffix: null,
  countryCode: null,
};

/**
 * Clear existing markers and plot the given place groups as small
 * circle dots on the map.  Accepts an array of { places, style }
 * objects so multiple suffixes show in different colours.
 */
function plotMarkers(groups) {
  // Remove previous layer
  if (markerLayer) {
    map.removeLayer(markerLayer);
  }

  markerLayer = L.layerGroup();

  // Backward-compat: if called with a plain array, wrap it
  if (Array.isArray(groups) && groups.length > 0 && !groups[0].places) {
    groups = [{ places: groups, style: DOT_STYLE }];
  }

  groups.forEach(({ places, style }) => {
    places.forEach((p) => {
      const dot = L.circleMarker([p.lat, p.lon], style);
      dot.bindTooltip(
        `<strong>${p.name}</strong><br/>Pop. ${p.population.toLocaleString()}`,
        { direction: "top", offset: [0, -6] }
      );
      markerLayer.addLayer(dot);
    });
  });

  map.addLayer(markerLayer);

  // Fit map bounds to results (if any)
  const allLayers = markerLayer.getLayers();
  if (allLayers.length > 0) {
    const bounds = L.featureGroup(allLayers).getBounds();
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 10 });
  }
}

// ── Suffix highlighting mode ────────────────────────────────────────

/**
 * Highlight all places with a specific suffix.
 * Only shows places matching the suffix, not the rest.
 */
async function highlightSuffix(suffix, countryCode) {
  if (!suffix || !countryCode) return;
  
  // Load country data if needed
  const places = await loadCountryData(countryCode);
  
  // Update highlight state
  currentHighlight = {
    active: true,
    suffix: suffix,
    countryCode: countryCode,
  };
  
  // Filter places by suffix
  const highlighted = filterBySuffix(places, suffix);
  
  // Plot only the highlighted places
  const groups = [
    { places: highlighted, style: DOT_STYLE_HIGHLIGHT },
  ];
  
  plotMarkers(groups);
  
  // Update UI to show what's highlighted
  updateHighlightInfo(suffix, highlighted.length);
}

/**
 * Clear the highlight mode and return to normal search view.
 */
function clearHighlight() {
  currentHighlight = {
    active: false,
    suffix: null,
    countryCode: null,
  };
  
  // Clear highlight info
  const infoEl = document.getElementById("highlight-info");
  if (infoEl) {
    infoEl.textContent = "";
    infoEl.style.display = "none";
  }
  
  // Re-run normal search
  search();
}

/**
 * Update the UI to show current highlight information.
 */
function updateHighlightInfo(suffix, count) {
  const infoEl = document.getElementById("highlight-info");
  if (infoEl) {
    infoEl.textContent = `Showing: "${suffix}" (${count} places) — `;
    infoEl.style.display = "block";
    
    // Add clear button if not already present
    if (!infoEl.querySelector(".clear-highlight-btn")) {
      const clearBtn = document.createElement("button");
      clearBtn.textContent = "Clear";
      clearBtn.className = "clear-highlight-btn";
      clearBtn.onclick = clearHighlight;
      infoEl.appendChild(clearBtn);
    }
  }
}

// ── Regional suffix analysis ────────────────────────────────────────

/**
 * Determine a simple regional label based on centroid position
 * relative to the bounding box of all places.
 */
function getRegionLabel(lat, lon, allPlaces) {
  const lats = allPlaces.map((p) => p.lat);
  const lons = allPlaces.map((p) => p.lon);
  
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  
  const latRange = maxLat - minLat;
  const lonRange = maxLon - minLon;
  
  // Thresholds for regional classification
  const northThreshold = minLat + latRange * 0.6;
  const southThreshold = minLat + latRange * 0.4;
  const eastThreshold = minLon + lonRange * 0.6;
  const westThreshold = minLon + lonRange * 0.4;
  
  let region = "";
  
  if (lat > northThreshold) region = "Northern";
  else if (lat < southThreshold) region = "Southern";
  else region = "Central";
  
  if (lonRange > latRange * 0.5) {
    // Country is wide enough to distinguish east/west
    if (lon > eastThreshold) region += " Eastern";
    else if (lon < westThreshold) region += " Western";
  }
  
  return region.trim();
}

/**
 * Analyze place names in a country to find regional suffixes.
 * Uses geographic entropy to identify suffixes that cluster in specific regions.
 * Low entropy = concentrated/regional. High entropy = uniformly distributed.
 * 
 * @param {Array} places - Array of place objects with name, lat, lon
 * @param {Number} minLength - Minimum suffix length (default 2)
 * @param {Number} maxLength - Maximum suffix length (default 5)
 * @param {Number} minOccurrences - Minimum times a suffix must appear (default 10)
 * @param {Number} maxResults - Maximum number of results to return (default 30)
 * @returns {Array} Array of {suffix, count, entropy, centroid, region}
 */
function analyzeSuffixes(places, minLength = 2, maxLength = 5, minOccurrences = 10, maxResults = 30) {
  if (!places || places.length === 0) return [];
  
  // Calculate bounding box for grid
  const lats = places.map((p) => p.lat);
  const lons = places.map((p) => p.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  
  // Create a grid (6x6 gives good granularity without being too fine)
  const gridSize = 6;
  const latStep = (maxLat - minLat) / gridSize;
  const lonStep = (maxLon - minLon) / gridSize;
  
  // Helper function to get grid cell for a place
  function getGridCell(lat, lon) {
    const row = Math.min(Math.floor((lat - minLat) / latStep), gridSize - 1);
    const col = Math.min(Math.floor((lon - minLon) / lonStep), gridSize - 1);
    return row * gridSize + col;
  }
  
  // Build a map of suffix → array of places
  const suffixMap = new Map();
  
  places.forEach((place) => {
    const name = place.name.toLowerCase();
    // Extract suffixes of various lengths
    for (let len = minLength; len <= maxLength; len++) {
      if (name.length > len) {
        const suffix = name.slice(-len);
        if (!suffixMap.has(suffix)) {
          suffixMap.set(suffix, []);
        }
        suffixMap.get(suffix).push(place);
      }
    }
  });
  
  // Calculate entropy for each suffix
  const results = [];
  
  suffixMap.forEach((suffixPlaces, suffix) => {
    if (suffixPlaces.length < minOccurrences) return;
    
    // Count how many places with this suffix are in each grid cell
    const cellCounts = new Array(gridSize * gridSize).fill(0);
    suffixPlaces.forEach((p) => {
      const cell = getGridCell(p.lat, p.lon);
      cellCounts[cell]++;
    });
    
    // Calculate Shannon entropy
    let entropy = 0;
    const total = suffixPlaces.length;
    for (const count of cellCounts) {
      if (count > 0) {
        const p = count / total;
        entropy -= p * Math.log2(p);
      }
    }
    
    // Calculate centroid for region labeling
    const lats = suffixPlaces.map((p) => p.lat);
    const lons = suffixPlaces.map((p) => p.lon);
    const meanLat = lats.reduce((sum, v) => sum + v, 0) / lats.length;
    const meanLon = lons.reduce((sum, v) => sum + v, 0) / lons.length;
    
    const region = getRegionLabel(meanLat, meanLon, places);
    
    results.push({
      suffix: suffix,
      count: suffixPlaces.length,
      entropy: entropy,
      centroid: { lat: meanLat, lon: meanLon },
      region: region,
    });
  });
  
  // Sort by entropy (ascending - lower entropy = more regional)
  results.sort((a, b) => a.entropy - b.entropy);
  
  // Filter out redundant sub-suffixes
  // For example, if "-eim" and "-heim" have similar counts, keep only "-heim"
  const filtered = [];
  const used = new Set();
  
  for (const result of results) {
    if (used.has(result.suffix)) continue;
    
    // Check if this suffix is contained in a longer suffix with similar count
    let isRedundant = false;
    for (const other of results) {
      if (other.suffix === result.suffix) continue;
      if (other.suffix.length <= result.suffix.length) continue;
      
      // Check if other ends with this suffix
      if (other.suffix.endsWith(result.suffix)) {
        // Compare counts - if within 20% or same, the shorter one is redundant
        const countDiff = Math.abs(result.count - other.count);
        const maxCount = Math.max(result.count, other.count);
        const tolerance = maxCount * 0.2;
        
        if (countDiff <= tolerance) {
          isRedundant = true;
          used.add(result.suffix);
          break;
        }
      }
    }
    
    if (!isRedundant) {
      filtered.push(result);
      if (filtered.length >= maxResults) break;
    }
  }
  
  return filtered;
}

/**
 * Populate the regional suffixes sidebar with suggestions.
 */
async function updateRegionalSuggestions() {
  const panel = document.getElementById("regional-suffixes-panel");
  const listEl = document.getElementById("regional-suffixes-list");
  const countries = getSelectedCountries();
  
  if (!panel || !listEl) return;
  
  // Hide panel if no country selected
  if (countries.length === 0) {
    panel.style.display = "none";
    return;
  }
  
  // Show loading state
  panel.style.display = "flex";
  listEl.innerHTML = '<div class="loading">Analyzing suffixes...</div>';
  
  try {
    // Load country data
    const countryCode = countries[0];
    const places = await loadCountryData(countryCode);
    
    // Filter by minimum population
    const minPop = getMinPopulation();
    const filteredPlaces = filterByPopulation(places, minPop);
    
    // Analyze suffixes with user-specified minimum
    const minPlaces = getMinPlaces();
    const suggestions = analyzeSuffixes(filteredPlaces, 2, 5, minPlaces, 30);
    
    // Clear loading and populate
    listEl.innerHTML = "";
    
    if (suggestions.length === 0) {
      listEl.innerHTML = '<div class="no-results">No regional patterns found</div>';
      return;
    }
    
    // Create suffix cards
    suggestions.forEach((item) => {
      const card = document.createElement("button");
      card.className = "suffix-card";
      card.innerHTML = `
        <div class="suffix-name">-${item.suffix}</div>
        <div class="suffix-info">${item.count} places · <span class="suffix-score">entropy ${item.entropy.toFixed(3)}</span></div>
        <div class="suffix-region">${item.region}</div>
      `;
      card.onclick = () => highlightSuffix(item.suffix, countryCode);
      listEl.appendChild(card);
    });
  } catch (error) {
    console.error("Failed to analyze suffixes:", error);
    listEl.innerHTML = '<div class="error">Failed to analyze suffixes</div>';
  }
}

// ── Main search routine ─────────────────────────────────────────────

async function search() {
  const countries = getSelectedCountries();
  const suffixes = getAllSuffixes();
  const minPop = getMinPopulation();

  // Check if any suffix has content
  const hasAnySuffix = suffixes.some(s => s.value.trim().length > 0);

  // Nothing selected or no suffixes → clear map
  if (countries.length === 0 || !hasAnySuffix) {
    plotMarkers([]);
    setResultCount(0);
    return;
  }

  // Load all selected country data in parallel
  const datasets = await Promise.all(countries.map(loadCountryData));
  const merged = datasets.flat();

  const groups = [];
  let totalCount = 0;

  // Process each suffix input
  suffixes.forEach(suffix => {
    if (suffix.value.trim().length > 0) {
      const results = filterByPopulation(filterBySuffix(merged, suffix.value), minPop);
      const style = createMarkerStyle(suffix.colors);
      groups.push({ places: results, style });
      totalCount += results.length;
    }
  });

  plotMarkers(groups);
  setResultCount(totalCount);
}

// ── Debounce helper ─────────────────────────────────────────────────

function debounce(fn, ms) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), ms);
  };
}

// ── Populate country dropdown ───────────────────────────────────────

/**
 * Populate the country dropdown from window.__geodata.countries.
 * Called on page load after countries.js has been loaded.
 */
function populateCountryDropdown() {
  const select = document.getElementById("country-select");
  const countries = window.__geodata?.countries || [];
  
  // Clear existing options except the placeholder
  while (select.options.length > 1) {
    select.remove(1);
  }
  
  // Sort countries alphabetically by name
  const sortedCountries = [...countries].sort((a, b) => 
    a.name.localeCompare(b.name)
  );
  
  // Add options for each available country
  sortedCountries.forEach(country => {
    const option = document.createElement("option");
    option.value = country.code;
    option.textContent = country.name;
    select.appendChild(option);
  });
}

// ── Event wiring ────────────────────────────────────────────────────

document.getElementById("population-input").addEventListener("input", () => {
  debounce(search, 300)();
  debounce(updateRegionalSuggestions, 300)();
});
document.getElementById("min-places-input").addEventListener("input", () => {
  debounce(updateRegionalSuggestions, 300)();
});
document.getElementById("country-select").addEventListener("change", () => {
  clearHighlight(); // Clear any active highlight
  search();
  updateRegionalSuggestions();
});
document.getElementById("add-suffix-btn").addEventListener("click", () => {
  createSuffixInput();
});

// ── Initialize on page load ─────────────────────────────────────────

populateCountryDropdown();
initializeSuffixInputs();

// ── Expose internals for browser-based tests ────────────────────────
const App = {
  cache,
  loadCountryData,
  filterBySuffix,
  filterByPopulation,
  getSelectedCountries,
  getAllSuffixes,
  getMinPopulation,
  getMinPlaces,
  setResultCount,
  plotMarkers,
  search,
  populateCountryDropdown,
  analyzeSuffixes,
  highlightSuffix,
  clearHighlight,
  updateRegionalSuggestions,
  createMarkerStyle,
  DOT_STYLE_FADED,
  DOT_STYLE_HIGHLIGHT,
  createSuffixInput,
  removeSuffixInput,
  initializeSuffixInputs,
};
