# Plan: GeoNames Suffix Search Map

## Goal
Create a small personal web page that:
- Searches for place name suffixes (e.g., "-by", "-ville")
- Finds matching cities in GeoNames data
- Plots those cities on an interactive map

## Requirements
### Runtime
- **uv** — Python package manager and runner
- **Python 3.8+** — managed via uv
- **Web browser** — for running the static site and JS tests

### Python Packages (via uv)
- `pytest` — unit testing for preprocessing script

### JavaScript Testing
- Browser-based testing with `console.assert()` (no npm/Node.js needed)
- Create `tests.js` + `test.html` to run tests in browser console

### Frontend (CDN, no install needed)
- **Leaflet.js** — map rendering
- **Leaflet.markercluster** — marker clustering plugin

## Recommended Approach
### 1) Data Source
Use the GeoNames country files already in Geonames/ (SE.txt, FR.txt). Add more by downloading additional country extracts from geonames.org when needed.

### 2) Data Parsing
- Input files are tab-delimited UTF-8.
- Use the “geoname” table columns described in Geonames/readme.txt.
- Only keep needed fields to reduce memory:
  - `geonameid`, `name`, `asciiname`, `latitude`, `longitude`, `feature class`, `feature code`, `country code`, `population`
- Filter to feature class `P` (cities, villages, etc.) to avoid non-city points.

### 3) Suffix Search
- Use `asciiname` field for matching (pre-computed by GeoNames).
- Strip diacritics from user input only, then match against `asciiname.lower()`.
- Population filter with default threshold of 500 to limit results and avoid marker overload.

### 4) Map Data / Visualization
Use a hosted map tile provider (no local map data needed):
- Recommended: OpenStreetMap tiles via Leaflet.js.
- You do **not** need to download map data; Leaflet can render tiles directly.

### 5) UI
- A single HTML page with:
  - Input for suffix
  - Country selection (checkboxes or dropdown)
  - Population filter (default: 500)
  - Result count
  - Map with markers or clustered markers

### 6) App Structure (Simple Static Site)
- `index.html` – UI, map container, scripts
- `app.js` – data loading, filtering, map plotting
- `data/` – preprocessed JSON for each country

### 7) Data Loading Strategy
Use **lazy loading with caching** to scale well as countries are added:
- Load country JSON only when selected (not all at once on page load).
- Cache loaded data in memory so toggling countries is instant after first load.
- Benefits: fast initial load, scales to many countries, low memory until needed.

### 8) Preprocessing
Recommended to preprocess the GeoNames TXT into smaller JSON for the browser:
- Write a small script to parse SE.txt / FR.txt.
- Output JSON: array of `{ name, asciiname, lat, lon, country, population }`
- Optionally gzip or compress for faster loading.

## Implementation Steps
1. **Create preprocessing script** (Python) to parse the GeoNames files.
   - Set up pytest and write tests alongside the code.
2. **Generate JSON** for SE and FR as a starting dataset.
3. **Build the webpage**:
   - Lazy load country JSON on selection (with in-memory caching)
   - Filter by suffix, feature class, and population (default: 500)
   - Plot results on Leaflet map
   - Set up Vitest and write tests for search logic.
4. **Add UX improvements**:
   - Result list and marker clustering
   - Toggle countries

## Notes on Licensing
- GeoNames: CC-BY 4.0 (already noted in Geonames/readme.txt)
- OpenStreetMap tiles: OSM has attribution requirements; show the attribution in the map.

## Next Files to Create
- `index.html`
- `app.js`
- `style.css`
- `scripts/parse_geonames.py` (or `scripts/parse_geonames.js`)
- `data/SE.json`, `data/FR.json`
