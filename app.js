// ── Map initialisation ──────────────────────────────────────────────
const map = L.map("map").setView([54, 10], 4); // Center on northern Europe

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution:
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);
