"""Tests for scripts/parse_geonames.py — line parsing & feature class filtering."""

import sys
from pathlib import Path

# Make the scripts package importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from parse_geonames import filter_feature_class, parse_line, write_js, validate_country_code  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A valid GeoNames line has 19 tab-separated columns.
# Columns: geonameid, name, asciiname, alternatenames, lat, lon,
#          feature_class, feature_code, country_code, cc2,
#          admin1, admin2, admin3, admin4, population,
#          elevation, dem, timezone, modification_date
VALID_LINE = (
    "2673730\t"          # 0  geonameid
    "Stockholm\t"        # 1  name
    "Stockholm\t"        # 2  asciiname
    "Stokholmo,Estocolmo\t"  # 3  alternatenames
    "59.33258\t"         # 4  latitude
    "18.0649\t"          # 5  longitude
    "P\t"                # 6  feature class
    "PPLC\t"             # 7  feature code
    "SE\t"               # 8  country code
    "\t"                 # 9  cc2
    "26\t"               # 10 admin1
    "0180\t"             # 11 admin2
    "\t"                 # 12 admin3
    "\t"                 # 13 admin4
    "1515017\t"          # 14 population
    "28\t"               # 15 elevation
    "32\t"               # 16 dem
    "Europe/Stockholm\t" # 17 timezone
    "2024-10-06"         # 18 modification date
)


# ---------------------------------------------------------------------------
# Tests — parse_line: valid lines
# ---------------------------------------------------------------------------

class TestParseLineValid:
    def test_parses_name(self):
        rec = parse_line(VALID_LINE)
        assert rec is not None
        assert rec["name"] == "Stockholm"

    def test_parses_lat_lon(self):
        rec = parse_line(VALID_LINE)
        assert abs(rec["lat"] - 59.33258) < 1e-5
        assert abs(rec["lon"] - 18.0649) < 1e-4

    def test_parses_feature_class(self):
        rec = parse_line(VALID_LINE)
        assert rec["feature_class"] == "P"

    def test_parses_country(self):
        rec = parse_line(VALID_LINE)
        assert rec["country"] == "SE"

    def test_parses_population(self):
        rec = parse_line(VALID_LINE)
        assert rec["population"] == 1515017

    def test_parses_geonameid(self):
        rec = parse_line(VALID_LINE)
        assert rec["geonameid"] == "2673730"


# ---------------------------------------------------------------------------
# Tests — parse_line: missing / malformed data
# ---------------------------------------------------------------------------

class TestParseLineMalformed:
    def test_empty_string_returns_none(self):
        assert parse_line("") is None

    def test_blank_line_returns_none(self):
        assert parse_line("\n") is None

    def test_too_few_columns_returns_none(self):
        # Only 5 columns instead of 19
        assert parse_line("1\tFoo\tFoo\t\t59.0") is None

    def test_non_numeric_latitude_returns_none(self):
        bad = VALID_LINE.replace("59.33258", "not_a_number")
        assert parse_line(bad) is None

    def test_non_numeric_longitude_returns_none(self):
        bad = VALID_LINE.replace("18.0649", "xyz")
        assert parse_line(bad) is None

    def test_non_numeric_population_defaults_to_zero(self):
        bad = VALID_LINE.replace("1515017", "N/A")
        rec = parse_line(bad)
        assert rec is not None
        assert rec["population"] == 0

    def test_empty_population_defaults_to_zero(self):
        bad = VALID_LINE.replace("1515017", "")
        rec = parse_line(bad)
        assert rec is not None
        assert rec["population"] == 0


# ---------------------------------------------------------------------------
# Tests — filter_feature_class
# ---------------------------------------------------------------------------

class TestFilterFeatureClass:
    def test_accepts_class_P(self):
        rec = parse_line(VALID_LINE)
        assert filter_feature_class(rec) is True

    def test_rejects_class_T(self):
        line_T = VALID_LINE.replace("\tP\t", "\tT\t")
        rec = parse_line(line_T)
        assert filter_feature_class(rec) is False

    def test_rejects_class_H(self):
        line_H = VALID_LINE.replace("\tP\t", "\tH\t")
        rec = parse_line(line_H)
        assert filter_feature_class(rec) is False

    def test_rejects_class_S(self):
        line_S = VALID_LINE.replace("\tP\t", "\tS\t")
        rec = parse_line(line_S)
        assert filter_feature_class(rec) is False

    def test_rejects_class_A(self):
        line_A = VALID_LINE.replace("\tP\t", "\tA\t")
        rec = parse_line(line_A)
        assert filter_feature_class(rec) is False

    def test_rejects_class_L(self):
        line_L = VALID_LINE.replace("\tP\t", "\tL\t")
        rec = parse_line(line_L)
        assert filter_feature_class(rec) is False

    def test_custom_allowed_class(self):
        line_T = VALID_LINE.replace("\tP\t", "\tT\t")
        rec = parse_line(line_T)
        assert filter_feature_class(rec, allowed="T") is True


# ---------------------------------------------------------------------------
# Tests — write_js
# ---------------------------------------------------------------------------

class TestWriteJs:
    def test_output_starts_with_geodata_init(self, tmp_path):
        out = tmp_path / "TEST.js"
        write_js([{"name": "A"}], out, "TEST")
        content = out.read_text(encoding="utf-8")
        assert content.startswith("window.__geodata = window.__geodata || {};\n")

    def test_output_contains_country_assignment(self, tmp_path):
        out = tmp_path / "SE.js"
        write_js([{"name": "X"}], out, "SE")
        content = out.read_text(encoding="utf-8")
        assert 'window.__geodata["SE"] = ' in content

    def test_output_contains_valid_json_array(self, tmp_path):
        import json
        records = [{"name": "Å", "lat": 1.5}]
        out = tmp_path / "SE.js"
        write_js(records, out, "SE")
        content = out.read_text(encoding="utf-8")
        # Extract the JSON portion after the assignment
        json_str = content.split(" = ", 1)[1].split(" = ", 1)[1].rstrip(";\n")
        parsed = json.loads(json_str)
        assert parsed == records

    def test_preserves_unicode(self, tmp_path):
        out = tmp_path / "FR.js"
        write_js([{"name": "Château"}], out, "FR")
        content = out.read_text(encoding="utf-8")
        assert "Château" in content


# ---------------------------------------------------------------------------
# Tests — validate_country_code
# ---------------------------------------------------------------------------

class TestValidateCountryCode:
    def test_accepts_valid_uppercase_codes(self):
        assert validate_country_code("SE") is True
        assert validate_country_code("FR") is True
        assert validate_country_code("NO") is True
        assert validate_country_code("ES") is True

    def test_rejects_lowercase_codes(self):
        assert validate_country_code("se") is False
        assert validate_country_code("fr") is False

    def test_rejects_mixed_case(self):
        assert validate_country_code("Se") is False
        assert validate_country_code("sE") is False

    def test_rejects_single_letter(self):
        assert validate_country_code("S") is False

    def test_rejects_three_letters(self):
        assert validate_country_code("SWE") is False

    def test_rejects_numbers(self):
        assert validate_country_code("S1") is False
        assert validate_country_code("12") is False

    def test_rejects_empty_string(self):
        assert validate_country_code("") is False

    def test_rejects_special_characters(self):
        assert validate_country_code("S-") is False
        assert validate_country_code("S_") is False


# ---------------------------------------------------------------------------
# Tests — download_country (mocked)
# ---------------------------------------------------------------------------

class TestDownloadCountry:
    """Test download_country function with mocked network calls."""

    def test_rejects_invalid_country_code(self, tmp_path):
        """Should reject invalid country codes without attempting download."""
        from parse_geonames import download_country
        
        result = download_country("se", tmp_path, force=False)
        assert result is False
        
        result = download_country("SWE", tmp_path, force=False)
        assert result is False

    def test_skips_existing_country_without_force(self, tmp_path):
        """Should skip download if country data already exists and force=False."""
        from parse_geonames import download_country
        
        # Create existing file
        geonames_dir = tmp_path / "Geonames" / "geoname"
        geonames_dir.mkdir(parents=True, exist_ok=True)
        existing_file = geonames_dir / "SE.txt"
        existing_file.write_text("existing data")
        
        result = download_country("SE", tmp_path, force=False)
        assert result is False
        assert existing_file.read_text() == "existing data"

    def test_overwrites_with_force_flag(self, tmp_path):
        """Should attempt download if force=True even when file exists."""
        from parse_geonames import download_country
        from unittest.mock import patch, MagicMock
        import zipfile
        import io
        
        # Create existing file
        geonames_dir = tmp_path / "Geonames" / "geoname"
        geonames_dir.mkdir(parents=True, exist_ok=True)
        existing_file = geonames_dir / "SE.txt"
        existing_file.write_text("old data")
        
        # Mock the download
        mock_zip = io.BytesIO()
        with zipfile.ZipFile(mock_zip, 'w') as zf:
            zf.writestr("SE.txt", "new data from geonames")
        mock_zip.seek(0)
        
        mock_response = MagicMock()
        mock_response.read.return_value = mock_zip.read()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        
        with patch('parse_geonames.urlopen', return_value=mock_response):
            result = download_country("SE", tmp_path, force=True)
        
        assert result is True
        assert existing_file.read_text() == "new data from geonames"

    def test_handles_404_error_gracefully(self, tmp_path):
        """Should return False and print error message on 404."""
        from parse_geonames import download_country
        from unittest.mock import patch
        from urllib.error import HTTPError
        
        mock_error = HTTPError("url", 404, "Not Found", {}, None)
        
        with patch('parse_geonames.urlopen', side_effect=mock_error):
            result = download_country("ZZ", tmp_path, force=False)
        
        assert result is False

    def test_handles_network_error_gracefully(self, tmp_path):
        """Should return False and print error message on network failure."""
        from parse_geonames import download_country
        from unittest.mock import patch
        from urllib.error import URLError
        
        mock_error = URLError("Network unreachable")
        
        with patch('parse_geonames.urlopen', side_effect=mock_error):
            result = download_country("NO", tmp_path, force=False)
        
        assert result is False

    def test_successful_download_and_extraction(self, tmp_path):
        """Should successfully download and extract a country zip file."""
        from parse_geonames import download_country
        from unittest.mock import patch, MagicMock
        import zipfile
        import io
        
        # Create a mock zip file with country data
        mock_zip = io.BytesIO()
        with zipfile.ZipFile(mock_zip, 'w') as zf:
            zf.writestr("NO.txt", "mock geonames data for Norway")
        mock_zip.seek(0)
        
        mock_response = MagicMock()
        mock_response.read.return_value = mock_zip.read()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        
        with patch('parse_geonames.urlopen', return_value=mock_response):
            result = download_country("NO", tmp_path, force=False)
        
        assert result is True
        
        # Verify file was extracted
        output_file = tmp_path / "Geonames" / "geoname" / "NO.txt"
        assert output_file.exists()
        assert output_file.read_text() == "mock geonames data for Norway"

    def test_handles_corrupted_zip(self, tmp_path):
        """Should handle corrupted zip files gracefully."""
        from parse_geonames import download_country
        from unittest.mock import patch, MagicMock
        
        mock_response = MagicMock()
        mock_response.read.return_value = b"not a valid zip file"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        
        with patch('parse_geonames.urlopen', return_value=mock_response):
            result = download_country("IT", tmp_path, force=False)
        
        assert result is False

