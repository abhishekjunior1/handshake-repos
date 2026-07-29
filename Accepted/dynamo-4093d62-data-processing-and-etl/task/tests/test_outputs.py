"""
Tests for the data validation pipeline output.

Verifies that the pipeline produces correct results on the hidden test dataset,
checking quality scores, violation counts, and structural integrity of the report.
"""

import json
import math
import os

EXPECTED_PATH = "/tests/expected_output.json"
OUTPUT_PATH = "/app/output.json"


def load_json(path):
    """Load and parse a JSON file from the given path."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_output_file_exists():
    """Verify that the pipeline produced an output file at the expected path."""
    assert os.path.exists(OUTPUT_PATH), f"Output file not found at {OUTPUT_PATH}"


def test_output_valid_json():
    """Verify that the output file contains valid JSON."""
    try:
        load_json(OUTPUT_PATH)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        assert False, f"Output is not valid JSON: {e}"


def test_dataset_name():
    """Verify the dataset name in the output matches expected."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    assert output["dataset"] == expected["dataset"], (
        f"Dataset name mismatch: got '{output['dataset']}', "
        f"expected '{expected['dataset']}'"
    )


def test_table_count():
    """Verify the correct number of tables are present in the output."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    assert set(output["tables"].keys()) == set(expected["tables"].keys()), (
        f"Table names mismatch: got {set(output['tables'].keys())}, "
        f"expected {set(expected['tables'].keys())}"
    )


def test_products_record_counts():
    """Verify the products table has correct valid and invalid record counts."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_products = output["tables"]["products"]
    exp_products = expected["tables"]["products"]
    assert out_products["total_records"] == exp_products["total_records"], (
        f"Products total_records: got {out_products['total_records']}, "
        f"expected {exp_products['total_records']}"
    )
    assert out_products["valid_records"] == exp_products["valid_records"], (
        f"Products valid_records: got {out_products['valid_records']}, "
        f"expected {exp_products['valid_records']}"
    )
    assert out_products["invalid_records"] == exp_products["invalid_records"], (
        f"Products invalid_records: got {out_products['invalid_records']}, "
        f"expected {exp_products['invalid_records']}"
    )


def test_orders_record_counts():
    """Verify the orders table has correct valid and invalid record counts."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_orders = output["tables"]["orders"]
    exp_orders = expected["tables"]["orders"]
    assert out_orders["total_records"] == exp_orders["total_records"], (
        f"Orders total_records: got {out_orders['total_records']}, "
        f"expected {exp_orders['total_records']}"
    )
    assert out_orders["valid_records"] == exp_orders["valid_records"], (
        f"Orders valid_records: got {out_orders['valid_records']}, "
        f"expected {exp_orders['valid_records']}"
    )
    assert out_orders["invalid_records"] == exp_orders["invalid_records"], (
        f"Orders invalid_records: got {out_orders['invalid_records']}, "
        f"expected {exp_orders['invalid_records']}"
    )


def test_products_overall_score():
    """Verify the products table overall quality score is correct."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_score = output["tables"]["products"]["overall_score"]
    exp_score = expected["tables"]["products"]["overall_score"]
    assert math.isclose(out_score, exp_score, rel_tol=1e-3), (
        f"Products overall_score: got {out_score}, expected {exp_score}"
    )


def test_orders_overall_score():
    """Verify the orders table overall quality score is correct."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_score = output["tables"]["orders"]["overall_score"]
    exp_score = expected["tables"]["orders"]["overall_score"]
    assert math.isclose(out_score, exp_score, rel_tol=1e-3), (
        f"Orders overall_score: got {out_score}, expected {exp_score}"
    )


def test_products_column_scores():
    """Verify per-column quality scores for the products table."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_scores = output["tables"]["products"]["column_scores"]
    exp_scores = expected["tables"]["products"]["column_scores"]
    for col, exp_val in exp_scores.items():
        assert col in out_scores, f"Missing column score for '{col}' in products"
        assert math.isclose(out_scores[col], exp_val, rel_tol=1e-3), (
            f"Products column_score[{col}]: got {out_scores[col]}, expected {exp_val}"
        )


def test_orders_column_scores():
    """Verify per-column quality scores for the orders table."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_scores = output["tables"]["orders"]["column_scores"]
    exp_scores = expected["tables"]["orders"]["column_scores"]
    for col, exp_val in exp_scores.items():
        assert col in out_scores, f"Missing column score for '{col}' in orders"
        assert math.isclose(out_scores[col], exp_val, rel_tol=1e-3), (
            f"Orders column_score[{col}]: got {out_scores[col]}, expected {exp_val}"
        )


def test_products_violation_count():
    """Verify the number of constraint violations in the products table."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_count = len(output["tables"]["products"]["violations"])
    exp_count = len(expected["tables"]["products"]["violations"])
    assert out_count == exp_count, (
        f"Products violations count: got {out_count}, expected {exp_count}"
    )


def test_orders_violation_count():
    """Verify the number of constraint violations in the orders table."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_count = len(output["tables"]["orders"]["violations"])
    exp_count = len(expected["tables"]["orders"]["violations"])
    assert out_count == exp_count, (
        f"Orders violations count: got {out_count}, expected {exp_count}"
    )


def test_products_conditional_violations():
    """Verify conditional validation violations in the products table."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_count = len(output["tables"]["products"]["conditional_violations"])
    exp_count = len(expected["tables"]["products"]["conditional_violations"])
    assert out_count == exp_count, (
        f"Products conditional_violations count: got {out_count}, expected {exp_count}"
    )


def test_orders_conditional_violations():
    """Verify conditional validation violations in the orders table."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_count = len(output["tables"]["orders"]["conditional_violations"])
    exp_count = len(expected["tables"]["orders"]["conditional_violations"])
    assert out_count == exp_count, (
        f"Orders conditional_violations count: got {out_count}, expected {exp_count}"
    )


def test_orders_integrity_violations():
    """Verify referential integrity violations in the orders table."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_count = len(output["tables"]["orders"]["integrity_violations"])
    exp_count = len(expected["tables"]["orders"]["integrity_violations"])
    assert out_count == exp_count, (
        f"Orders integrity_violations count: got {out_count}, expected {exp_count}"
    )


def test_products_no_integrity_violations():
    """Verify products table has no integrity violations (no foreign keys)."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_count = len(output["tables"]["products"].get("integrity_violations", []))
    exp_count = len(expected["tables"]["products"].get("integrity_violations", []))
    assert out_count == exp_count, (
        f"Products integrity_violations count: got {out_count}, expected {exp_count}"
    )


def test_violation_structure():
    """Verify that violations have the correct structure with required fields."""
    output = load_json(OUTPUT_PATH)
    required_fields = {"record_index", "column", "rule", "value", "message"}
    for table_name, table_data in output["tables"].items():
        for v in table_data.get("violations", []):
            missing = required_fields - set(v.keys())
            assert not missing, (
                f"Violation in {table_name} missing fields: {missing}"
            )


def test_conditional_violation_details():
    """Verify conditional violation records reference correct columns and rules."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    for table_name in expected["tables"]:
        out_conds = output["tables"][table_name]["conditional_violations"]
        exp_conds = expected["tables"][table_name]["conditional_violations"]
        out_cols = sorted([v["column"] for v in out_conds])
        exp_cols = sorted([v["column"] for v in exp_conds])
        assert out_cols == exp_cols, (
            f"{table_name} conditional violation columns: got {out_cols}, "
            f"expected {exp_cols}"
        )


def test_integrity_violation_values():
    """Verify integrity violations reference the correct orphaned foreign key values."""
    output = load_json(OUTPUT_PATH)
    expected = load_json(EXPECTED_PATH)
    out_vals = sorted(
        [v["value"] for v in output["tables"]["orders"]["integrity_violations"]]
    )
    exp_vals = sorted(
        [v["value"] for v in expected["tables"]["orders"]["integrity_violations"]]
    )
    assert out_vals == exp_vals, (
        f"Orders integrity violation values: got {out_vals}, expected {exp_vals}"
    )
