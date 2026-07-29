"""
Oracle solution: patches all bugs in the survival analysis pipeline and runs it.
"""

import subprocess
import sys


def patch_kaplan_meier():
    """Fix Bug 1: KM _effective_at_risk subtracts censorings from at-risk count."""
    filepath = "/app/kaplan_meier.py"
    with open(filepath, "r") as f:
        content = f.read()

    # The buggy _effective_at_risk subtracts censorings: n_total - n_censored
    # Fix: return n_total directly (censorings leave AFTER events at same time)
    content = content.replace(
        "    return n_total - n_censored",
        "    return n_total",
    )

    with open(filepath, "w") as f:
        f.write(content)


def patch_log_rank():
    """Fix Bug 2: Log-rank variance uses n as population correction instead of (n-1)."""
    filepath = "/app/log_rank.py"
    with open(filepath, "r") as f:
        content = f.read()

    # The buggy code uses population_correction = n
    # Fix: use (n - 1) for the finite population correction factor
    content = content.replace(
        "    population_correction = n\n",
        "    population_correction = n - 1\n",
    )

    with open(filepath, "w") as f:
        f.write(content)


def patch_cox_model():
    """Fix Bug 3: Cox partial likelihood processes tied events sequentially instead of batched."""
    filepath = "/app/cox_model.py"
    with open(filepath, "r") as f:
        content = f.read()

    # Replace the sequential processing with batched Breslow method
    old_code = '''    for i in range(n):
        # Add patient i to risk set
        risk_sum += exp_xb[i]
        for j in range(n_features):
            risk_sum_x[j] += X[i][j] * exp_xb[i]
            for k in range(n_features):
                risk_sum_xx[j][k] += X[i][j] * X[i][k] * exp_xb[i]

        # If this patient had an event, contribute to likelihood
        if events[i] == 1 and risk_sum > 0:
            xb_i = sum(X[i][j] * beta[j] for j in range(n_features))
            log_likelihood += xb_i - math.log(risk_sum)

            for j in range(n_features):
                gradient[j] += X[i][j] - risk_sum_x[j] / risk_sum

                for k in range(n_features):
                    hessian[j][k] -= (
                        risk_sum_xx[j][k] / risk_sum
                        - (risk_sum_x[j] * risk_sum_x[k]) / (risk_sum ** 2)
                    )'''

    new_code = '''    i = 0
    while i < n:
        # Find all patients at the same time (Breslow: batch tied events)
        current_time = times[i]
        j = i
        while j < n and times[j] == current_time:
            j += 1

        # Add ALL patients at this time to risk set first
        for k in range(i, j):
            risk_sum += exp_xb[k]
            for f in range(n_features):
                risk_sum_x[f] += X[k][f] * exp_xb[k]
                for g in range(n_features):
                    risk_sum_xx[f][g] += X[k][f] * X[k][g] * exp_xb[k]

        # Then process event contributions using the SAME risk set
        for k in range(i, j):
            if events[k] == 1 and risk_sum > 0:
                xb_i = sum(X[k][f] * beta[f] for f in range(n_features))
                log_likelihood += xb_i - math.log(risk_sum)

                for f in range(n_features):
                    gradient[f] += X[k][f] - risk_sum_x[f] / risk_sum

                    for g in range(n_features):
                        hessian[f][g] -= (
                            risk_sum_xx[f][g] / risk_sum
                            - (risk_sum_x[f] * risk_sum_x[g]) / (risk_sum ** 2)
                        )

        i = j'''

    content = content.replace(old_code, new_code)

    with open(filepath, "w") as f:
        f.write(content)


def run_pipeline():
    """Run the fixed pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)


if __name__ == "__main__":
    patch_kaplan_meier()
    patch_log_rank()
    patch_cox_model()
    run_pipeline()
