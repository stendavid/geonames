"""Parse GeoNames tab-delimited TXT files into compact JSON for the browser."""

import json
import sys
from pathlib import Path
from typing import List, Dict

# Column indices in the GeoNames "geoname" table (tab-delimited)
COL_GEONAMEID = 0
COL_NAME = 1
COL_LATITUDE = 4
COL_LONGITUDE = 5
COL_FEATURE_CLASS = 6
COL_FEATURE_CODE = 7
COL_COUNTRY_CODE = 8
COL_POPULATION = 14

EXPECTED_MIN_COLUMNS = 19


def parse_line(line: str) -> dict | None:
    """Parse a single tab-delimited GeoNames line into a dict.

    Returns None if the line is blank or has fewer columns than expected.
    """
    line = line.rstrip("\n\r")
    if not line:
        return None

    fields = line.split("\t")
    if len(fields) < EXPECTED_MIN_COLUMNS:
        return None

    try:
        latitude = float(fields[COL_LATITUDE])
        longitude = float(fields[COL_LONGITUDE])
    except (ValueError, IndexError):
        return None

    try:
        population = int(fields[COL_POPULATION])
    except (ValueError, IndexError):
        population = 0

    return {
        "geonameid": fields[COL_GEONAMEID],
        "name": fields[COL_NAME],
        "lat": latitude,
        "lon": longitude,
        "feature_class": fields[COL_FEATURE_CLASS],
        "feature_code": fields[COL_FEATURE_CODE],
        "country": fields[COL_COUNTRY_CODE],
        "population": population,
    }


def filter_feature_class(record: dict, allowed: str = "P") -> bool:
    """Return True if the record's feature_class is in the allowed set."""
    return record.get("feature_class") == allowed


def slim_record(record: dict) -> dict:
    """Return only the fields needed by the frontend."""
    return {
        "name": record["name"],
        "lat": record["lat"],
        "lon": record["lon"],
        "country": record["country"],
        "population": record["population"],
    }


def parse_file(input_path: Path) -> list[dict]:
    """Parse an entire GeoNames TXT file, returning slim P-class records."""
    results = []
    with open(input_path, encoding="utf-8") as fh:
        for line in fh:
            record = parse_line(line)
            if record is None:
                continue
            if not filter_feature_class(record):
                continue
            results.append(slim_record(record))
    return results


def write_json(records: list[dict], output_path: Path) -> None:
    """Write records as a JSON array."""
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, ensure_ascii=False, indent=1)


def write_js(records: list[dict], output_path: Path, country_code: str) -> None:
    """Write records as a JS file that registers data on window.__geodata.

    The generated file looks like:
        window.__geodata = window.__geodata || {};
        window.__geodata["SE"] = [ ... ];
    This allows loading via a <script> tag without needing an HTTP server.
    """
    json_blob = json.dumps(records, ensure_ascii=False)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("window.__geodata = window.__geodata || {};\n")
        fh.write(f'window.__geodata["{country_code}"] = {json_blob};\n')


def parse_country_info(country_info_path: Path) -> Dict[str, str]:
    """Parse countryInfo.txt and return a dict of country_code -> country_name.
    
    The file is tab-delimited. The ISO code (column 0) and country name (column 4)
    are extracted. Lines starting with '#' are skipped.
    """
    countries = {}
    with open(country_info_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            
            fields = line.split("\t")
            if len(fields) >= 5:
                iso_code = fields[0]
                country_name = fields[4]
                if iso_code and country_name:
                    countries[iso_code] = country_name
    
    return countries


def get_available_countries(data_dir: Path) -> List[str]:
    """Scan data directory for .json files and return list of country codes."""
    country_codes = []
    for json_file in sorted(data_dir.glob("*.json")):
        code = json_file.stem
        # Exclude the allCountries file
        if code != "allCountries":
            country_codes.append(code)
    return country_codes


def generate_countries_metadata(
    data_dir: Path,
    country_info_path: Path,
    output_path: Path
) -> None:
    """Generate countries.js metadata file for the browser.
    
    Scans the data directory for available country data files and creates
    a JS file with country code and name pairs.
    """
    # Get country name mappings
    country_names = parse_country_info(country_info_path)
    
    # Get available country codes from data directory
    available_codes = get_available_countries(data_dir)
    
    # Build metadata list
    countries_metadata = []
    for code in available_codes:
        country_name = country_names.get(code, code)  # Fall back to code if name not found
        countries_metadata.append({
            "code": code,
            "name": country_name
        })
    
    # Write as JS file
    json_blob = json.dumps(countries_metadata, ensure_ascii=False, indent=2)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("window.__geodata = window.__geodata || {};\n")
        fh.write(f"window.__geodata.countries = {json_blob};\n")
    
    print(f"Generated countries metadata with {len(countries_metadata)} countries: {output_path}")


def main(input_path: str, output_path: str) -> None:
    """CLI entry point: parse a GeoNames TXT file and write JSON + JS."""
    inp = Path(input_path)
    out = Path(output_path)

    if not inp.exists():
        print(f"Error: input file not found: {inp}", file=sys.stderr)
        sys.exit(1)

    out.parent.mkdir(parents=True, exist_ok=True)

    records = parse_file(inp)

    # Derive country code from input filename (e.g. SE.txt → SE)
    country_code = inp.stem

    # Write JSON
    write_json(records, out)
    print(f"Wrote {len(records)} records to {out}")

    # Write JS alongside the JSON (e.g. data/SE.js next to data/SE.json)
    js_out = out.with_suffix(".js")
    write_js(records, js_out, country_code)
    print(f"Wrote {len(records)} records to {js_out}")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--generate-countries":
        # Generate countries.js metadata file
        workspace_root = Path(__file__).parent.parent
        data_dir = workspace_root / "data"
        country_info_path = workspace_root / "Geonames" / "countryInfo.txt"
        output_path = data_dir / "countries.js"
        
        if not country_info_path.exists():
            print(f"Error: {country_info_path} not found", file=sys.stderr)
            sys.exit(1)
        
        generate_countries_metadata(data_dir, country_info_path, output_path)
    elif len(sys.argv) == 3:
        # Parse geonames data file
        main(sys.argv[1], sys.argv[2])
    else:
        print(f"Usage:", file=sys.stderr)
        print(f"  {sys.argv[0]} <input.txt> <output.json>  - Parse geonames data", file=sys.stderr)
        print(f"  {sys.argv[0]} --generate-countries       - Generate countries metadata", file=sys.stderr)
        sys.exit(1)
