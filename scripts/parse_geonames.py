"""Parse GeoNames tab-delimited TXT files into compact JSON for the browser."""

import argparse
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import List, Dict
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

# GeoNames download URL base
GEONAMES_DOWNLOAD_URL = "https://download.geonames.org/export/dump/"

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
    """Scan data directory for .js files and return list of country codes."""
    country_codes = []
    for js_file in sorted(data_dir.glob("*.js")):
        code = js_file.stem
        # Exclude the countries metadata file
        if code != "countries":
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


def validate_country_code(country_code: str) -> bool:
    """Validate that country code is 2 uppercase letters."""
    return bool(re.match(r'^[A-Z]{2}$', country_code))


def download_country(country_code: str, workspace_root: Path, force: bool = False) -> bool:
    """Download a country's GeoNames data from geonames.org.
    
    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., 'ES', 'NO')
        workspace_root: Root directory of the workspace
        force: If True, overwrite existing files
    
    Returns:
        True if download successful, False otherwise
    """
    # Validate country code format
    if not validate_country_code(country_code):
        print(f"Error: Invalid country code '{country_code}'. Must be 2 uppercase letters.", file=sys.stderr)
        return False
    
    # Set up paths
    geonames_dir = workspace_root / "Geonames" / "geoname"
    geonames_dir.mkdir(parents=True, exist_ok=True)
    
    output_txt = geonames_dir / f"{country_code}.txt"
    
    # Check if file already exists
    if output_txt.exists() and not force:
        print(f"Country '{country_code}' already exists at {output_txt}")
        print(f"Use --force flag to overwrite existing data.")
        return False
    
    # Download the zip file
    zip_url = f"{GEONAMES_DOWNLOAD_URL}{country_code}.zip"
    print(f"Downloading {country_code} from {zip_url}...")
    
    try:
        with urlopen(zip_url) as response:
            zip_data = response.read()
    except HTTPError as e:
        if e.code == 404:
            print(f"Error: Country code '{country_code}' not found on geonames.org (404)", file=sys.stderr)
        else:
            print(f"Error: HTTP {e.code} when downloading {zip_url}", file=sys.stderr)
        return False
    except URLError as e:
        print(f"Error: Network error when downloading {zip_url}: {e.reason}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: Unexpected error when downloading: {e}", file=sys.stderr)
        return False
    
    # Extract the zip file
    print(f"Extracting {country_code}.zip...")
    try:
        # Write zip to temporary location
        temp_zip = geonames_dir / f"{country_code}.zip.tmp"
        with open(temp_zip, "wb") as f:
            f.write(zip_data)
        
        # Extract the txt file
        with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
            # The zip should contain a file named {country_code}.txt
            expected_filename = f"{country_code}.txt"
            if expected_filename not in zip_ref.namelist():
                print(f"Error: Expected file '{expected_filename}' not found in zip archive", file=sys.stderr)
                print(f"Archive contains: {zip_ref.namelist()}", file=sys.stderr)
                os.remove(temp_zip)
                return False
            
            # Extract to the geonames directory
            zip_ref.extract(expected_filename, geonames_dir)
        
        # Clean up temp zip file
        os.remove(temp_zip)
        print(f"Successfully downloaded and extracted {country_code} data to {output_txt}")
        return True
        
    except zipfile.BadZipFile:
        print(f"Error: Downloaded file is not a valid zip archive", file=sys.stderr)
        if temp_zip.exists():
            os.remove(temp_zip)
        return False
    except Exception as e:
        print(f"Error: Failed to extract zip file: {e}", file=sys.stderr)
        if temp_zip.exists():
            os.remove(temp_zip)
        return False


def download_and_process(country_code: str, workspace_root: Path, force: bool = False) -> bool:
    """Download a country's data and automatically parse it.
    
    This orchestrates the complete workflow:
    1. Download and extract the country data
    2. Parse it to JS format
    3. Regenerate the countries metadata
    
    Args:
        country_code: ISO 3166-1 alpha-2 country code
        workspace_root: Root directory of the workspace
        force: If True, overwrite existing files
    
    Returns:
        True if all steps successful, False otherwise
    """
    # Step 1: Download
    print(f"=== Downloading {country_code} ===")
    if not download_country(country_code, workspace_root, force):
        return False
    
    # Step 2: Parse to JS format
    print(f"\n=== Parsing {country_code} data ===")
    input_path = workspace_root / "Geonames" / "geoname" / f"{country_code}.txt"
    output_path = workspace_root / "data" / f"{country_code}.js"
    
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        records = parse_file(input_path)
        write_js(records, output_path, country_code)
        print(f"Wrote {len(records)} records to {output_path}")
    except Exception as e:
        print(f"Error: Failed to parse data: {e}", file=sys.stderr)
        return False
    
    # Step 3: Regenerate countries metadata
    print(f"\n=== Updating countries metadata ===")
    try:
        data_dir = workspace_root / "data"
        country_info_path = workspace_root / "Geonames" / "countryInfo.txt"
        countries_output = data_dir / "countries.js"
        
        if not country_info_path.exists():
            print(f"Warning: {country_info_path} not found. Skipping countries metadata update.", file=sys.stderr)
        else:
            generate_countries_metadata(data_dir, country_info_path, countries_output)
    except Exception as e:
        print(f"Error: Failed to update countries metadata: {e}", file=sys.stderr)
        return False
    
    print(f"\n✓ Successfully downloaded and processed {country_code}")
    return True


def main(input_path: str, output_path: str) -> None:
    """CLI entry point: parse a GeoNames TXT file and write JS."""
    inp = Path(input_path)
    out = Path(output_path)

    if not inp.exists():
        print(f"Error: input file not found: {inp}", file=sys.stderr)
        sys.exit(1)

    out.parent.mkdir(parents=True, exist_ok=True)

    records = parse_file(inp)

    # Derive country code from input filename (e.g. SE.txt → SE)
    country_code = inp.stem

    # Write JS file (e.g. data/SE.js)
    write_js(records, out, country_code)
    print(f"Wrote {len(records)} records to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse GeoNames data files and manage country downloads",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download and process a country automatically
  %(prog)s --download ES
  
  # Re-download and update existing country data
  %(prog)s --download NO --force
  
  # Parse a GeoNames data file manually
  %(prog)s Geonames/geoname/SE.txt data/SE.js
  
  # Generate countries metadata
  %(prog)s --generate-countries
"""
    )
    
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Input GeoNames TXT file to parse"
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        help="Output JS file path"
    )
    parser.add_argument(
        "--download",
        metavar="COUNTRY_CODE",
        help="Download and process a country by its ISO code (e.g., ES, NO, IT)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite of existing country data when using --download"
    )
    parser.add_argument(
        "--generate-countries",
        action="store_true",
        help="Generate countries.js metadata file from available data"
    )
    
    args = parser.parse_args()
    workspace_root = Path(__file__).parent.parent
    
    # Handle --download flag
    if args.download:
        country_code = args.download.upper()
        success = download_and_process(country_code, workspace_root, args.force)
        sys.exit(0 if success else 1)
    
    # Handle --generate-countries flag
    elif args.generate_countries:
        data_dir = workspace_root / "data"
        country_info_path = workspace_root / "Geonames" / "countryInfo.txt"
        output_path = data_dir / "countries.js"
        
        if not country_info_path.exists():
            print(f"Error: {country_info_path} not found", file=sys.stderr)
            sys.exit(1)
        
        generate_countries_metadata(data_dir, country_info_path, output_path)
    
    # Handle manual parsing mode
    elif args.input_file and args.output_file:
        main(args.input_file, args.output_file)
    
    # No valid arguments provided
    else:
        parser.print_help()
        sys.exit(1)
