// ── Browser-based tests for GeoNames Suffix Search ─────────────────
// Run by opening test.html in a browser and checking the console.

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
    console.log(`  ✅ ${message}`);
  } else {
    failed++;
    console.error(`  ❌ ${message}`);
  }
}

function section(title) {
  console.group(`\n🔹 ${title}`);
}

function endSection() {
  console.groupEnd();
}

// ── Sample data used by several tests ───────────────────────────────

const samplePlaces = [
  { name: "Granby",    asciiname: "Granby",    lat: 59.9, lon: 17.0, country: "SE", population: 1200 },
  { name: "Solby",     asciiname: "Solby",     lat: 60.1, lon: 16.5, country: "SE", population: 300 },
  { name: "Björkby",   asciiname: "Bjorkby",   lat: 60.5, lon: 17.2, country: "SE", population: 800 },
  { name: "Byron",     asciiname: "Byron",     lat: 58.0, lon: 15.0, country: "SE", population: 5000 },
  { name: "Stockholm", asciiname: "Stockholm", lat: 59.3, lon: 18.1, country: "SE", population: 975000 },
  { name: "Belleville", asciiname: "Belleville", lat: 48.8, lon: 2.4, country: "FR", population: 600 },
  { name: "Tinyville",  asciiname: "Tinyville",  lat: 47.0, lon: 2.0, country: "FR", population: 50 },
];

// ═══════════════════════════════════════════════════════════════════
// 1) Suffix search
// ═══════════════════════════════════════════════════════════════════

section("Suffix search – filterBySuffix");

(() => {
  const res = App.filterBySuffix(samplePlaces, "by");
  const names = res.map((p) => p.asciiname);
  assert(names.includes("Granby"), "Matches 'Granby' for suffix 'by'");
  assert(names.includes("Solby"), "Matches 'Solby' for suffix 'by'");
  assert(names.includes("Bjorkby"), "Matches 'Bjorkby' for suffix 'by'");
  assert(!names.includes("Byron"), "Does NOT match 'Byron' for suffix 'by'");
  assert(!names.includes("Stockholm"), "Does NOT match 'Stockholm' for suffix 'by'");
  assert(res.length === 3, `Returns exactly 3 results (got ${res.length})`);
})();

(() => {
  const res = App.filterBySuffix(samplePlaces, "BY");
  assert(res.length === 3, "Case-insensitive: 'BY' matches same 3 places");
})();

(() => {
  const res = App.filterBySuffix(samplePlaces, "ville");
  const names = res.map((p) => p.asciiname);
  assert(names.includes("Belleville"), "Matches 'Belleville' for suffix 'ville'");
  assert(names.includes("Tinyville"), "Matches 'Tinyville' for suffix 'ville'");
  assert(res.length === 2, `Returns exactly 2 results for 'ville' (got ${res.length})`);
})();

(() => {
  const res = App.filterBySuffix(samplePlaces, "");
  assert(res.length === 0, "Empty suffix returns no results");
})();

(() => {
  const res = App.filterBySuffix(samplePlaces, "   ");
  assert(res.length === 0, "Whitespace-only suffix returns no results");
})();

(() => {
  const res = App.filterBySuffix(samplePlaces, "zzz");
  assert(res.length === 0, "Non-matching suffix returns no results");
})();

endSection();

// ═══════════════════════════════════════════════════════════════════
// 2) Population filtering
// ═══════════════════════════════════════════════════════════════════

section("Population filtering – filterByPopulation");

(() => {
  const res = App.filterByPopulation(samplePlaces, 500);
  assert(res.length === 5, `5 places have pop ≥ 500 (got ${res.length})`);
  const names = res.map((p) => p.asciiname);
  assert(!names.includes("Solby"), "Solby (300) excluded at threshold 500");
  assert(!names.includes("Tinyville"), "Tinyville (50) excluded at threshold 500");
})();

(() => {
  const res = App.filterByPopulation(samplePlaces, 1200);
  assert(res.some((p) => p.asciiname === "Granby"), "Granby (1200) included at threshold 1200 (boundary)");
})();

(() => {
  const res = App.filterByPopulation(samplePlaces, 0);
  assert(res.length === samplePlaces.length, "Threshold 0 keeps all places");
})();

(() => {
  const res = App.filterByPopulation(samplePlaces, 1000000);
  assert(res.length === 0, "Very high threshold returns no results");
})();

endSection();

// ═══════════════════════════════════════════════════════════════════
// 3) Data caching
// ═══════════════════════════════════════════════════════════════════

section("Data caching – loadCountryData");

(() => {
  // Clear cache to start fresh
  for (const key of Object.keys(App.cache)) {
    delete App.cache[key];
  }

  assert(App.cache["SE"] === undefined, "Cache is empty before first load");

  // 1) Direct cache insertion — loadCountryData returns cached reference
  const fakeData = [{ name: "Testby", asciiname: "Testby", lat: 60, lon: 17, country: "SE", population: 100 }];
  App.cache["SE"] = fakeData;

  assert(App.cache["SE"] === fakeData, "Data is stored in cache after assignment");

  App.loadCountryData("SE").then((data) => {
    assert(data === fakeData, "loadCountryData returns cached reference (cache hit, no script load)");
    assert(data.length === 1, "Cached data has expected length");
  });

  // 2) Simulate window.__geodata pre-registration (as a data/*.js file would)
  delete App.cache["SE"];
  window.__geodata = window.__geodata || {};
  window.__geodata["_TEST_"] = [{ name: "Foo", asciiname: "Foo", lat: 0, lon: 0, country: "XX", population: 1 }];

  App.loadCountryData("_TEST_").then((data) => {
    assert(data === window.__geodata["_TEST_"], "loadCountryData picks up window.__geodata when cache is empty");
    assert(App.cache["_TEST_"] === data, "Result is then stored in cache");
    // Clean up
    delete App.cache["_TEST_"];
    delete window.__geodata["_TEST_"];
  });

  // 3) Verify FR is still not loaded
  assert(App.cache["FR"] === undefined, "FR is not loaded until requested");

  // Clean up
  delete App.cache["SE"];
})();

endSection();

// ═══════════════════════════════════════════════════════════════════
// Summary
// ═══════════════════════════════════════════════════════════════════
console.log("\n══════════════════════════════════════════════");
console.log(`Tests complete: ${passed} passed, ${failed} failed`);
console.log("══════════════════════════════════════════════\n");

document.getElementById("test-summary").textContent =
  `Tests complete: ${passed} passed, ${failed} failed`;
document.getElementById("test-summary").style.color =
  failed === 0 ? "#27ae60" : "#c0392b";
