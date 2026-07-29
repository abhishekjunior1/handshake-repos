"""
Test suite for the PCG solver pipeline.
Validates output on a 6x6 pentadiagonal SPD system.
"""

import json
import os
import pytest


@pytest.fixture
def output():
    """Load pipeline output."""
    path = "/app/output.json"
    assert os.path.exists(path), f"Output not found: {path}"
    with open(path, "r") as f:
        return json.load(f)


@pytest.fixture
def expected():
    """Load expected reference output."""
    path = "/tests/expected_output.json"
    assert os.path.exists(path), f"Expected output not found: {path}"
    with open(path, "r") as f:
        return json.load(f)


def test_pipeline_completed(output):
    """Pipeline must complete without errors."""
    assert output["status"] == "completed"


def test_solver_converged(output):
    """Solver must report convergence."""
    assert output["converged"] is True


def test_iteration_count(output):
    """Solver should require multiple iterations for this coupled system."""
    assert output["iterations"] >= 5, (
        f"Expected at least 5 iterations for a 6x6 coupled SPD system, "
        f"got {output['iterations']} — likely premature convergence"
    )


def test_solution_accuracy(output, expected):
    """Solution vector must match expected values within tight tolerance."""
    sol = output["solution"]
    exp_sol = expected["solution"]
    assert len(sol) == len(exp_sol), (
        f"Solution dimension mismatch: got {len(sol)}, expected {len(exp_sol)}"
    )
    for i in range(len(sol)):
        assert abs(sol[i] - exp_sol[i]) < 1e-6, (
            f"Solution component x[{i}] = {sol[i]:.8f}, "
            f"expected {exp_sol[i]:.8f}, error = {abs(sol[i] - exp_sol[i]):.2e}"
        )


def test_final_residual_small(output):
    """Final residual norm must be negligible for a converged solution."""
    assert output["final_residual_norm"] < 1e-8, (
        f"Final residual norm {output['final_residual_norm']:.2e} too large — "
        f"solution has not converged to sufficient accuracy"
    )


def test_relative_residual_below_tolerance(output):
    """Relative residual must be below the requested tolerance."""
    tol = output["tolerance_requested"]
    rel = output["relative_residual"]
    assert rel < tol, (
        f"Relative residual {rel:.2e} exceeds tolerance {tol:.2e}"
    )


def test_residual_norms_monotone(output):
    """Residual norms should decrease monotonically for SPD systems with PCG."""
    norms = output["residual_norms"]
    for i in range(1, len(norms)):
        assert norms[i] <= norms[i - 1] * (1 + 1e-10), (
            f"Residual increased at iteration {i}: "
            f"{norms[i]:.6e} > {norms[i-1]:.6e}"
        )


def test_residual_history_length(output):
    """Residual history should include the initial norm plus one entry per iteration."""
    actual_len = len(output["residual_norms"])
    # History starts with initial residual norm, then one entry per completed iteration
    assert actual_len >= 2, (
        f"Residual history has {actual_len} entries, expected at least 2"
    )
    assert actual_len == output["iterations"], (
        f"Residual history has {actual_len} entries, "
        f"expected {output['iterations']} (initial + iteration norms)"
    )


def test_condition_estimate_reasonable(output):
    """Condition number estimate should be at least 1.0 for any SPD system."""
    kappa = output["condition_estimate"]
    assert kappa >= 1.0, (
        f"Condition estimate {kappa:.4f} < 1.0 is physically impossible"
    )


def test_solver_metrics_present(output):
    """Output must contain solver performance metrics."""
    assert "solver_metrics" in output
    metrics = output["solver_metrics"]
    assert "efficiency" in metrics
    assert "solution_norm" in metrics
    assert metrics["efficiency"] > 0
