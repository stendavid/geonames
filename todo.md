# Todo: GeoNames Suffix Search Map

## Phase 1: Data Preprocessing
- [x] **Set up pytest** — Install pytest, create `tests/` directory
- [x] **Create preprocessing script** — Python script (`scripts/parse_geonames.py`) to parse GeoNames TXT files
- [x] **Test line parsing (pytest)** — Valid lines, missing fields, malformed data
- [x] **Test feature class filtering (pytest)** — Keep class `P`, reject others
- [x] **Parse SE.txt to JSON** — Generate `data/SE.json` with name, lat, lon, country, population
- [x] **Parse FR.txt to JSON** — Generate `data/FR.json` with the same structure

## Phase 2: Core Web Page
- [x] **Create index.html structure** — Basic HTML with input field, country selector, result count, map container
- [x] **Add Leaflet map container** — Include Leaflet.js CDN and configure OpenStreetMap tiles
- [x] **Create style.css** — Layout styling for the search UI and map

## Phase 3: Application Logic
- [ ] **Create test.html and tests.js** — Browser-based test runner using `console.assert()`
- [ ] **Build app.js - lazy loading** — Fetch country JSON on selection, cache in memory
- [ ] **Test data caching (console.assert)** — Verify cache hit/miss behavior
- [ ] **Build app.js - suffix search** — Normalize names (lowercase, strip diacritics), filter by `endsWith()`
- [ ] **Test diacritic stripping (console.assert)** — Normalize user input: `"Malmö"` → `"malmo"`, etc.
- [ ] **Test suffix matching (console.assert)** — Match/no-match cases, case insensitivity
- [ ] **Add population filter** — Minimum population threshold (default: 500)
- [ ] **Test population filtering (console.assert)** — Exclude cities below threshold
- [ ] **Build app.js - map plotting** — Add markers to Leaflet map for matching cities

## Phase 4: UX Improvements
- [ ] **Add country selection UI** — Checkboxes or dropdown to select SE, FR, or both
- [ ] **Add marker clustering** — Use Leaflet.markercluster for dense results
- [ ] **Add result list display** — Show matching place names alongside the map

## Phase 5: Polish
- [ ] **Add OSM attribution** — Required OpenStreetMap attribution in map corner
- [ ] **Test and refine UX** — Test suffix searches like "-by", "-ville", adjust UI
