"""Verification tests for the Shell Environment Profile Compiler."""
import json, os, pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output.json")

@pytest.fixture
def output_data():
    """Load pipeline output."""
    with open(OUTPUT_PATH) as f:
        return json.load(f)

@pytest.fixture
def expected_data():
    """Load expected output."""
    with open(EXPECTED_PATH) as f:
        return json.load(f)

class TestEnvironmentValues:
    """Tests for resolved environment variable values."""
    def test_all_values_match(self, output_data, expected_data):
        """Verify all resolved variable values match expected."""
        assert output_data["environment"] == expected_data["environment"]

    def test_variable_count(self, output_data, expected_data):
        """Verify correct number of variables exported."""
        assert len(output_data["environment"]) == len(expected_data["environment"])

    def test_environment_sorted(self, output_data, expected_data):
        """Verify environment keys are in sorted order as required by spec."""
        keys = list(output_data["environment"].keys())
        assert keys == sorted(keys), "Environment keys must be sorted alphabetically"

    def test_interpolation_resolved(self, output_data, expected_data):
        """Verify variable references are fully resolved regardless of definition order."""
        env = output_data["environment"]
        assert "${" not in env.get("SERVICE_URL", ""), \
            f"SERVICE_URL has unresolved ref: {env.get('SERVICE_URL')}"
        assert env.get("SERVICE_URL") == expected_data["environment"]["SERVICE_URL"]

    def test_multiline_values(self, output_data, expected_data):
        """Verify multiline values use actual newlines not literal backslash-n."""
        banner = output_data["environment"].get("SSH_BANNER", "")
        expected_banner = expected_data["environment"]["SSH_BANNER"]
        assert banner == expected_banner
        assert "\\n" not in banner, "SSH_BANNER should contain actual newlines, not literal \\n"

    def test_quote_handling(self, output_data, expected_data):
        """Verify quote stripping removes only the outermost enclosing pair."""
        env = output_data["environment"]
        exp = expected_data["environment"]
        assert env.get("JWT_SECRET") == exp["JWT_SECRET"]
        assert env.get("API_KEY") == exp["API_KEY"]

class TestMetadata:
    """Tests for output metadata."""
    def test_source_attribution(self, output_data, expected_data):
        """Verify source attribution matches."""
        assert output_data["metadata"]["source_attribution"] == expected_data["metadata"]["source_attribution"]

    def test_layer_summary(self, output_data, expected_data):
        """Verify layer summary matches."""
        assert output_data["metadata"]["layers"] == expected_data["metadata"]["layers"]

    def test_output_format(self, output_data, expected_data):
        """Verify version and format fields."""
        assert output_data["version"] == expected_data["version"]
        assert output_data["format"] == expected_data["format"]

    def test_case_sensitive_export_filtering(self, output_data, expected_data):
        """Verify case-sensitive prefix matching preserves lowercase variants."""
        env = output_data["environment"]
        # internal_note (lowercase) should be exported (not matched by INTERNAL_ prefix)
        assert "internal_note" in env, "Case-sensitive filtering should preserve lowercase 'internal_note'"


class TestFullOutput:
    """Final catch-all verification."""
    def test_full_output_match(self, output_data, expected_data):
        """Verify the complete pipeline output matches expected results exactly."""
        assert output_data == expected_data
