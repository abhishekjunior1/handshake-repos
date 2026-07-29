import json
import os
import pytest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# In Docker: output at /app/data/output.json, expected at /tests/expected_output.json
# Locally: relative to task directory
if os.path.exists("/app/data"):
    OUTPUT_PATH = "/app/data/output.json"
else:
    TASK_DIR = os.path.dirname(BASE_DIR)
    OUTPUT_PATH = os.path.join(TASK_DIR, "environment", "data", "output.json")

EXPECTED_PATH = os.path.join(BASE_DIR, "expected_output.json")


def load(path):
    with open(path, "r") as f:
        return json.load(f)


@pytest.fixture
def output():
    return load(OUTPUT_PATH)


@pytest.fixture
def expected():
    return load(EXPECTED_PATH)


def test_output_exists():
    """Pipeline produces output.json."""
    assert os.path.exists(OUTPUT_PATH), "output.json was not generated"


def test_record_count(output, expected):
    """Merged record count matches expected after deduplication."""
    assert output["metadata"]["merged_count"] == expected["metadata"]["merged_count"]


def test_no_duplicates(output):
    """No duplicate IDs remain in output records."""
    ids = [r["id"] for r in output["records"]]
    assert len(ids) == len(set(ids)), "Duplicate IDs found in output"


def test_upsert_preserves_fields(output, expected):
    """Upsert merge preserves non-null field values from partial updates."""
    output_map = {r["id"]: r for r in output["records"]}
    expected_map = {r["id"]: r for r in expected["records"]}

    for rec_id, exp_rec in expected_map.items():
        out_rec = output_map.get(rec_id)
        assert out_rec is not None, f"Missing record {rec_id}"
        for field in ["status", "priority", "description"]:
            if exp_rec.get(field) is not None:
                assert out_rec.get(field) == exp_rec.get(field), (
                    f"Record {rec_id} field {field}: got {out_rec.get(field)}, expected {exp_rec.get(field)}"
                )


def test_window_count(output, expected):
    """Correct number of aggregation time windows."""
    assert output["aggregation"]["total_windows"] == expected["aggregation"]["total_windows"]


def test_window_keys_match(output, expected):
    """Aggregation window keys match expected set."""
    out_keys = set(output["aggregation"]["windows"].keys())
    exp_keys = set(expected["aggregation"]["windows"].keys())
    assert out_keys == exp_keys, f"Window mismatch: got {out_keys}, expected {exp_keys}"


def test_aggregation_record_count(output, expected):
    """Total records processed in aggregation matches expected."""
    assert (
        output["aggregation"]["total_records_processed"]
        == expected["aggregation"]["total_records_processed"]
    )


def test_window_totals(output, expected):
    """Per-window record counts and totals match expected values."""
    for window_key, exp_window in expected["aggregation"]["windows"].items():
        out_window = output["aggregation"]["windows"].get(window_key)
        assert out_window is not None, f"Missing window {window_key}"
        assert out_window["record_count"] == exp_window["record_count"], (
            f"Window {window_key} count: got {out_window['record_count']}, expected {exp_window['record_count']}"
        )
        assert abs(out_window["total_adjusted_amount"] - exp_window["total_adjusted_amount"]) < 0.01, (
            f"Window {window_key} total: got {out_window['total_adjusted_amount']}, expected {exp_window['total_adjusted_amount']}"
        )


def test_scd_records_in_correct_window(output, expected):
    """SCD type-2 records are assigned to correct windows by effective_date."""
    out_windows = output["aggregation"]["windows"]
    exp_windows = expected["aggregation"]["windows"]
    for wk in exp_windows:
        assert wk in out_windows, f"Expected window {wk} not in output"
        assert out_windows[wk]["record_count"] == exp_windows[wk]["record_count"]
