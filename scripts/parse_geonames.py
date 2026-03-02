"""Parse GeoNames tab-delimited TXT files into compact JSON for the browser."""

import json
import sys
from pathlib import Path

# Column indices in the GeoNames "geoname" table (tab-delimited)
COL_GEONAMEID = 0
COL_NAME = 1
COL_ASCIINAME = 2
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
        "asciiname": fields[COL_ASCIINAME],
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
        "asciiname": record["asciiname"],
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
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.txt> <output.json>", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
