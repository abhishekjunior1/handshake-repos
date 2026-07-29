"""
Verification tests for the adaptive ODE solver pipeline.

Compares the agent's output against expected results from a correctly
implemented solver on the hidden test problem.
"""

import json
import os

EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
ACTUAL_OUTPUT_PATH = "/app/output.json"


def load_json(path):
    """Load and parse a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def approx_equal(a, b, rel_tol=1e-3, abs_tol=1e-6):
    """Check if two floating point numbers are approximately equal."""
    if a == b:
        return True
    if a is None or b is None:
        return a == b
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def test_output_file_exists():
    """Verify that the solver produced an output file at the expected path."""
    assert os.path.exists(ACTUAL_OUTPUT_PATH), (
        f"Output file not found at {ACTUAL_OUTPUT_PATH}"
    )


def test_output_is_valid_json():
    """Verify that the output file contains valid JSON."""
    try:
        load_json(ACTUAL_OUTPUT_PATH)
    except (json.JSONDecodeError, Exception) as e:
        assert False, f"Output is not valid JSON: {e}"


def test_problem_name():
    """Verify the problem name matches the expected value."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert actual["problem_name"] == expected["problem_name"]


def test_final_state():
    """Verify the final state values at the end of integration are correct."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for var in expected["final_state"]:
        assert var in actual["final_state"], f"Missing variable '{var}' in final state"
        assert approx_equal(actual["final_state"][var], expected["final_state"][var]), (
            f"Final state '{var}': got {actual['final_state'][var]}, "
            f"expected {expected['final_state'][var]}"
        )


def test_trajectory_length():
    """Verify the correct number of output points were generated."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert len(actual["trajectory"]) == len(expected["trajectory"]), (
        f"Trajectory length: got {len(actual['trajectory'])}, "
        f"expected {len(expected['trajectory'])}"
    )


def test_trajectory_midpoint():
    """Verify solution accuracy at the midpoint of the integration interval."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    mid_idx = len(expected["trajectory"]) // 2
    act_mid = actual["trajectory"][mid_idx]
    exp_mid = expected["trajectory"][mid_idx]

    for key in exp_mid:
        if key != "time" and isinstance(exp_mid[key], float):
            assert approx_equal(act_mid[key], exp_mid[key]), (
                f"Midpoint '{key}': got {act_mid[key]}, expected {exp_mid[key]}"
            )


def test_trajectory_quarter():
    """Verify solution accuracy at the quarter-point of the integration."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    q_idx = len(expected["trajectory"]) // 4
    act_q = actual["trajectory"][q_idx]
    exp_q = expected["trajectory"][q_idx]

    for key in exp_q:
        if key != "time" and isinstance(exp_q[key], float):
            assert approx_equal(act_q[key], exp_q[key]), (
                f"Quarter-point '{key}': got {act_q[key]}, expected {exp_q[key]}"
            )


def test_trajectory_three_quarter():
    """Verify solution accuracy at the three-quarter point of the integration."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    idx = 3 * len(expected["trajectory"]) // 4
    act = actual["trajectory"][idx]
    exp = expected["trajectory"][idx]

    for key in exp:
        if key != "time" and isinstance(exp[key], float):
            assert approx_equal(act[key], exp[key]), (
                f"Three-quarter '{key}': got {act[key]}, expected {exp[key]}"
            )


def test_integration_completed():
    """Verify the solver reached the end of the integration interval."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert approx_equal(
        actual["diagnostics"]["final_time"],
        expected["diagnostics"]["final_time"],
    ), (
        f"Final time: got {actual['diagnostics']['final_time']}, "
        f"expected {expected['diagnostics']['final_time']}"
    )


def test_solver_efficiency():
    """Verify the solver used a reasonable number of steps (not excessively many)."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    # The correct solver should use roughly similar step counts
    # Allow 3x tolerance for different but valid step selection
    exp_steps = expected["diagnostics"]["step_count"]
    act_steps = actual["diagnostics"]["step_count"]

    assert act_steps <= exp_steps * 3, (
        f"Too many steps: got {act_steps}, expected ~{exp_steps} "
        f"(max allowed: {exp_steps * 3})"
    )
