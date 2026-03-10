# GeoNames Browser Application

A lightweight web application for browsing geographical data from [GeoNames.org](https://www.geonames.org). This tool downloads, parses, and displays populated places (cities, towns, villages) for different countries.

## Features

- **Automated Country Downloads**: Download and process country data directly from GeoNames.org
- **Browser-Based**: View geographical data without needing a server
- **Filtered Data**: Focuses on populated places (feature class "P")
- **Compact Format**: Converts large GeoNames files into optimized JavaScript data

## Getting Started

### Download Country Data

Download and process a country automatically:

```bash
# Download Norway
uv run python scripts/parse_geonames.py --download NO

# Download Spain (case-insensitive)
uv run python scripts/parse_geonames.py --download es

# Re-download and update existing data
uv run python scripts/parse_geonames.py --download FR --force
```

The `--download` command will:
1. Download the country's `.zip` file from GeoNames.org
2. Extract it to `Geonames/geoname/`
3. Parse and filter to populated places only
4. Generate a JavaScript file in `data/`
5. Update the countries metadata automatically

### Manual Processing

You can also manually parse existing GeoNames files:

```bash
# Parse a country file
uv run python scripts/parse_geonames.py Geonames/geoname/SE.txt data/SE.js

# Regenerate countries metadata
uv run python scripts/parse_geonames.py --generate-countries
```

### View in Browser

Open `index.html` in your browser to view and search the geographical data.

## Command Reference

```bash
# Show help
uv run python scripts/parse_geonames.py --help

# Download a country
uv run python scripts/parse_geonames.py --download COUNTRY_CODE

# Force overwrite existing data
uv run python scripts/parse_geonames.py --download COUNTRY_CODE --force

# Parse a file manually
uv run python scripts/parse_geonames.py <input.txt> <output.js>

# Generate countries metadata
uv run python scripts/parse_geonames.py --generate-countries
```

## Data Format

**Input**: Tab-delimited GeoNames text files (19 columns, UTF-8)  
**Filter**: Feature class "P" (populated places) only  
**Output**: JavaScript files with compact records containing:
- `name`: Place name
- `lat`: Latitude
- `lon`: Longitude
- `country`: ISO country code
- `population`: Population count

## License

GeoNames data is licensed under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).

## Country Codes

Use ISO 3166-1 alpha-2 country codes (e.g., `US`, `GB`, `DE`, `IT`, `NO`, `SE`, `FR`, `ES`, `JP`, `CN`).

See the full list at [GeoNames Country Info](http://download.geonames.org/export/dump/countryInfo.txt).
