"""Patches pipeline.py data-flow bugs and runs the pipeline."""
import subprocess, sys


def patch():
    with open('/app/pipeline.py', 'r') as f:
        content = f.read()

    # Fix 1: Use bin centers instead of bin edges for model fitting
    content = content.replace(
        """    # Use bin boundaries as reference distances for model fitting
    lag_distances = bin_edges[1:]""",
        """    # Use bin centers as reference distances for model fitting
    lag_distances = bin_centers"""
    )

    # Fix 2: Pass total sill, not partial sill
    content = content.replace(
        """    # Pass partial sill for kriging covariance computation
    kriging_params = {
        'nugget': model_params['nugget'],
        'sill': model_params['sill'] - model_params['nugget'],
        'range': model_params['range'],
        'model_type': model_params['model_type']
    }""",
        """    # Pass model parameters to kriging
    kriging_params = {
        'nugget': model_params['nugget'],
        'sill': model_params['sill'],
        'range': model_params['range'],
        'model_type': model_params['model_type']
    }"""
    )

    # Fix 3: Use n - n_model_params for degrees of freedom
    content = content.replace(
        """    # Use full sample size for variance normalization
    n_model_params = 3  # nugget, sill, range
    df = n_points""",
        """    # Correct degrees of freedom: n - number of estimated parameters
    n_model_params = 3  # nugget, sill, range
    df = n_points - n_model_params"""
    )

    with open('/app/pipeline.py', 'w') as f:
        f.write(content)


if __name__ == '__main__':
    patch()
    r = subprocess.run(['python3', '/app/pipeline.py', '/app/config.json', '/app/output.json'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        sys.exit(1)
    print(r.stdout)
