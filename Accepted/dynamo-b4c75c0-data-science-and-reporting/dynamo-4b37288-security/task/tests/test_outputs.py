"""BinVault parser output validation."""
import json
import pytest

OUTPUT = "/app/output.json"
EXPECTED = "/tests/expected_output.json"


@pytest.fixture
def output_data():
    """Load parser output."""
    with open(OUTPUT) as f: return json.load(f)


@pytest.fixture
def expected_data():
    """Load expected output."""
    with open(EXPECTED) as f: return json.load(f)


class TestCompleteness:
    """All records parsed without errors."""

    def test_no_errors(self, output_data):
        """Zero parse errors in output."""
        assert output_data["summary"]["errors"] == 0

    def test_record_count(self, output_data, expected_data):
        """Correct number of records."""
        assert output_data["summary"]["total"] == expected_data["summary"]["total"]

    def test_type_distribution(self, output_data, expected_data):
        """Record type counts match."""
        assert output_data["summary"]["types"] == expected_data["summary"]["types"]


class TestBlobs:
    """BLOB integrity checks."""

    def test_all_checksums_valid(self, output_data):
        """All BLOB checksums must pass."""
        blobs = [r for r in output_data["records"] if r.get("type") == "BLOB"]
        for b in blobs:
            assert b["checksum_valid"] is True, f"BLOB {b['blob_id']} checksum failed"

    def test_blob_lengths(self, output_data, expected_data):
        """BLOB decoded lengths match."""
        actual = [r for r in output_data["records"] if r.get("type") == "BLOB"]
        expected = [r for r in expected_data["records"] if r.get("type") == "BLOB"]
        for a, e in zip(actual, expected):
            assert a["data_length"] == e["data_length"]


class TestDeltas:
    """DELTA record validation."""

    def test_delta_count(self, output_data, expected_data):
        """All DELTA records present."""
        actual = [r for r in output_data["records"] if r.get("type") == "DELTA"]
        expected = [r for r in expected_data["records"] if r.get("type") == "DELTA"]
        assert len(actual) == len(expected)

    def test_delta_ops(self, output_data, expected_data):
        """DELTA operations match."""
        actual = [r for r in output_data["records"] if r.get("type") == "DELTA"]
        expected = [r for r in expected_data["records"] if r.get("type") == "DELTA"]
        for a, e in zip(actual, expected):
            assert a["operations"] == e["operations"]


class TestXrefs:
    """XREF record validation."""

    def test_xref_count(self, output_data, expected_data):
        """All XREF records present."""
        actual = [r for r in output_data["records"] if r.get("type") == "XREF"]
        expected = [r for r in expected_data["records"] if r.get("type") == "XREF"]
        assert len(actual) == len(expected)

    def test_xref_entries(self, output_data, expected_data):
        """XREF entries match."""
        actual = [r for r in output_data["records"] if r.get("type") == "XREF"]
        expected = [r for r in expected_data["records"] if r.get("type") == "XREF"]
        for a, e in zip(actual, expected):
            assert a["entries"] == e["entries"]


class TestFull:
    """Complete output match."""

    def test_exact_match(self, output_data, expected_data):
        """Full output must match expected exactly."""
        assert output_data["records"] == expected_data["records"]
