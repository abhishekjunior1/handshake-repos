"""Tests for the NestedConf parser/serializer pipeline output.

Verifies that the pipeline correctly handles:
- Multi-section configurations with cross-references
- Escape sequence processing in quoted strings
- Section name preservation in output
- Chained variable reference resolution
"""

import json
import os

EXPECTED_PATH = "/tests/expected_output.json"
OUTPUT_PATH = "/app/output.json"


def load_output():
    """Load the pipeline output JSON."""
    assert os.path.exists(OUTPUT_PATH), f"Output file not found at {OUTPUT_PATH}"
    with open(OUTPUT_PATH) as f:
        return json.load(f)


def load_expected():
    """Load the expected output JSON."""
    assert os.path.exists(EXPECTED_PATH), f"Expected output not found at {EXPECTED_PATH}"
    with open(EXPECTED_PATH) as f:
        return json.load(f)


def test_output_file_exists():
    """Verify that the pipeline produces an output file at the expected path."""
    assert os.path.exists(OUTPUT_PATH), "Pipeline did not produce output.json"


def test_output_is_valid_json():
    """Verify that the output file contains valid JSON."""
    with open(OUTPUT_PATH) as f:
        content = f.read()
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        assert False, f"Output is not valid JSON: {e}"


def test_config_section_names():
    """Verify that section names in the config output preserve original casing."""
    output = load_output()
    expected = load_expected()
    assert list(output["config"].keys()) == list(expected["config"].keys()), (
        f"Section names differ: got {list(output['config'].keys())}, "
        f"expected {list(expected['config'].keys())}"
    )


def test_sections_order():
    """Verify that sections_order in document_info preserves original case."""
    output = load_output()
    expected = load_expected()
    assert output["document_info"]["sections_order"] == expected["document_info"]["sections_order"], (
        f"sections_order differs: got {output['document_info']['sections_order']}, "
        f"expected {expected['document_info']['sections_order']}"
    )


def test_escape_sequences_backslash():
    """Verify that double-backslash escape sequences produce literal backslashes."""
    output = load_output()
    expected = load_expected()
    # Check that paths with backslashes are correctly escaped
    env_section = None
    for key, val in output["config"].items():
        if key.lower() == "environment":
            env_section = val
            break
    assert env_section is not None, "Environment section not found in output"

    expected_env = expected["config"]["Environment"]
    assert env_section.get("root_dir") == expected_env["root_dir"], (
        f"root_dir escape error: got {repr(env_section.get('root_dir'))}, "
        f"expected {repr(expected_env['root_dir'])}"
    )
    assert env_section.get("temp_path") == expected_env["temp_path"], (
        f"temp_path escape error: got {repr(env_section.get('temp_path'))}, "
        f"expected {repr(expected_env['temp_path'])}"
    )


def test_chained_reference_resolution():
    """Verify that chained references (A->B->C) are fully resolved."""
    output = load_output()
    expected = load_expected()
    # AppConfig.install_path should resolve through Paths.base_dir to Environment.root_dir
    app_section = None
    for key, val in output["config"].items():
        if key.lower() == "appconfig":
            app_section = val
            break
    assert app_section is not None, "AppConfig section not found"

    expected_app = expected["config"]["AppConfig"]
    assert app_section.get("install_path") == expected_app["install_path"], (
        f"Chained ref not resolved: install_path got {repr(app_section.get('install_path'))}, "
        f"expected {repr(expected_app['install_path'])}"
    )
    assert app_section.get("data_path") == expected_app["data_path"], (
        f"Chained ref not resolved: data_path got {repr(app_section.get('data_path'))}, "
        f"expected {repr(expected_app['data_path'])}"
    )
    assert app_section.get("temp_dir") == expected_app["temp_dir"], (
        f"Chained ref not resolved: temp_dir got {repr(app_section.get('temp_dir'))}, "
        f"expected {repr(expected_app['temp_dir'])}"
    )


def test_direct_reference_resolution():
    """Verify that direct (non-chained) references resolve correctly."""
    output = load_output()
    expected = load_expected()
    # DatabaseSettings values referenced directly by AppConfig
    app_section = None
    for key, val in output["config"].items():
        if key.lower() == "appconfig":
            app_section = val
            break
    assert app_section is not None, "AppConfig section not found"

    expected_app = expected["config"]["AppConfig"]
    assert app_section.get("db_host") == expected_app["db_host"], (
        f"Direct ref error: db_host got {repr(app_section.get('db_host'))}, "
        f"expected {repr(expected_app['db_host'])}"
    )
    assert app_section.get("db_port") == expected_app["db_port"], (
        f"Direct ref error: db_port got {repr(app_section.get('db_port'))}, "
        f"expected {repr(expected_app['db_port'])}"
    )


def test_logging_section_resolution():
    """Verify that the Logging section resolves its chained references."""
    output = load_output()
    expected = load_expected()
    log_section = None
    for key, val in output["config"].items():
        if key.lower() == "logging":
            log_section = val
            break
    assert log_section is not None, "Logging section not found"

    expected_log = expected["config"]["Logging"]
    assert log_section.get("output_dir") == expected_log["output_dir"], (
        f"Logging.output_dir not resolved: got {repr(log_section.get('output_dir'))}, "
        f"expected {repr(expected_log['output_dir'])}"
    )


def test_no_unresolved_references():
    """Verify that no unresolved ${...} references remain in the output values."""
    output = load_output()
    for section_name, section_vals in output["config"].items():
        for key, value in section_vals.items():
            assert "${" not in str(value), (
                f"Unresolved reference in {section_name}.{key}: {repr(value)}"
            )


def test_resolution_info():
    """Verify resolution metadata reports no unresolved references."""
    output = load_output()
    expected = load_expected()
    assert output["resolution_info"]["unresolved"] == expected["resolution_info"]["unresolved"], (
        f"Unresolved refs differ: got {output['resolution_info']['unresolved']}, "
        f"expected {expected['resolution_info']['unresolved']}"
    )
    assert output["resolution_info"]["circular"] == expected["resolution_info"]["circular"], (
        f"Circular refs differ: got {output['resolution_info']['circular']}"
    )


def test_has_references_flag():
    """Verify the has_references flag correctly reports no remaining references."""
    output = load_output()
    expected = load_expected()
    assert output["document_info"]["has_references"] == expected["document_info"]["has_references"], (
        f"has_references flag wrong: got {output['document_info']['has_references']}, "
        f"expected {expected['document_info']['has_references']}"
    )


def test_section_count():
    """Verify the document reports the correct number of sections."""
    output = load_output()
    expected = load_expected()
    assert output["document_info"]["section_count"] == expected["document_info"]["section_count"], (
        f"section_count wrong: got {output['document_info']['section_count']}, "
        f"expected {expected['document_info']['section_count']}"
    )


def test_total_keys():
    """Verify the document reports the correct total number of keys."""
    output = load_output()
    expected = load_expected()
    assert output["document_info"]["total_keys"] == expected["document_info"]["total_keys"], (
        f"total_keys wrong: got {output['document_info']['total_keys']}, "
        f"expected {expected['document_info']['total_keys']}"
    )


def test_dependencies_graph():
    """Verify that the dependency graph is correctly computed."""
    output = load_output()
    expected = load_expected()
    assert output["document_info"]["dependencies"] == expected["document_info"]["dependencies"], (
        f"Dependencies differ: got {output['document_info']['dependencies']}, "
        f"expected {expected['document_info']['dependencies']}"
    )


def test_full_output_match():
    """Verify that the entire output matches the expected output exactly."""
    output = load_output()
    expected = load_expected()
    assert output == expected, (
        "Full output does not match expected. Check section names, "
        "resolved values, and escape sequences."
    )
