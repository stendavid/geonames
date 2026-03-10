# GeoNames Place Name Suffix Explorer

An interactive web application for exploring and visualizing place name patterns by their suffixes. Search for places ending in specific suffixes (like "-by", "-ville", "-burg") and see where they appear on a map. This tool helps discover linguistic and historical settlement patterns across different countries.

## Usage

**1. Download country data:**

```bash
# Download a country (e.g., Norway)
uv run python scripts/parse_geonames.py --download NO

# Re-download/update existing data
uv run python scripts/parse_geonames.py --download FR --force
```

**2. Open `index.html` in your browser**

Search for suffix patterns like:
- `-by` (Scandinavian: "village")
- `-ville` (French: "town")  
- `-burg` (Germanic: "fortress")
- `-heim` (Germanic: "home")
- `-stad` (Dutch/Swedish: "city")

Use ISO 3166-1 alpha-2 country codes: `US`, `GB`, `DE`, `IT`, `NO`, `SE`, `FR`, `ES`, `JP`, etc.

## License

GeoNames data is licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
