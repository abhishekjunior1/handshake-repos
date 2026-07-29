"""
Cox proportional hazards model module for the survival analysis pipeline.

Implements the Cox PH model using Newton-Raphson optimization of the
partial likelihood. Handles tied event times using the Breslow
approximation for the risk set contribution.

Also computes the concordance index (C-statistic) for model discrimination
and hazard ratios with confidence intervals.
"""

import math


def fit_cox_model(patients, time_field, event_field, covariate_fields,
                  max_iter=100, tol=1e-9):
    """
    Fit a Cox proportional hazards model via Newton-Raphson optimization
    of the partial log-likelihood.

    The partial log-likelihood for the Breslow method is:
        L(beta) = sum_{events} [ x_i'beta - log(sum_{j in R_i} exp(x_j'beta)) ]

    where R_i is the risk set at time t_i.

    Parameters
    ----------
    patients : list of dict
        Patient records with covariates.
    time_field : str
        Key for survival time.
    event_field : str
        Key for event indicator.
    covariate_fields : list of str
        Names of covariates to include in the model.
    max_iter : int
        Maximum Newton-Raphson iterations.
    tol : float
        Convergence tolerance for log-likelihood change.

    Returns
    -------
    dict
        Fitted model with 'coefficients', 'standard_errors',
        'log_likelihood', 'n_iterations', 'converged' fields.
    """
    # Encode covariates as numeric matrix
    X, feature_names = _encode_covariates(patients, covariate_fields)
    n_features = len(feature_names)
    n_patients = len(patients)

    # Extract times and events
    times = [float(p[time_field]) for p in patients]
    events = [int(p[event_field]) for p in patients]

    # Sort by time (descending for efficient risk set computation)
    order = sorted(range(n_patients), key=lambda i: -times[i])
    times_sorted = [times[i] for i in order]
    events_sorted = [events[i] for i in order]
    X_sorted = [X[i] for i in order]

    # Initialize coefficients
    beta = [0.0] * n_features
    prev_ll = -float("inf")

    for iteration in range(max_iter):
        # Compute log-likelihood, gradient, and Hessian
        ll, gradient, hessian = _compute_likelihood_components(
            X_sorted, times_sorted, events_sorted, beta, n_features
        )

        # Check convergence
        if abs(ll - prev_ll) < tol:
            break
        prev_ll = ll

        # Newton-Raphson update: beta_new = beta - H^(-1) * g
        # Solve H * delta = g
        delta = _solve_linear_system(hessian, gradient, n_features)
        if delta is None:
            break

        beta = [beta[j] + delta[j] for j in range(n_features)]

    # Compute standard errors from inverse Hessian
    _, _, final_hessian = _compute_likelihood_components(
        X_sorted, times_sorted, events_sorted, beta, n_features
    )
    neg_hessian = [[-final_hessian[i][j] for j in range(n_features)]
                   for i in range(n_features)]
    inv_hessian = _invert_matrix(neg_hessian, n_features)

    standard_errors = []
    for j in range(n_features):
        if inv_hessian and inv_hessian[j][j] > 0:
            standard_errors.append(math.sqrt(inv_hessian[j][j]))
        else:
            standard_errors.append(0.0)

    return {
        "coefficients": {feature_names[j]: round(beta[j], 10) for j in range(n_features)},
        "standard_errors": {feature_names[j]: round(standard_errors[j], 10) for j in range(n_features)},
        "log_likelihood": round(prev_ll, 10),
        "n_iterations": iteration + 1,
        "converged": abs(ll - prev_ll) < tol if iteration < max_iter - 1 else False,
    }


def compute_concordance_index(patients, time_field, event_field, coefficients,
                              covariate_fields):
    """
    Compute Harrell's concordance index (C-statistic) for a fitted Cox model.

    The concordance index measures the proportion of concordant pairs
    among all comparable (permissible) pairs. A pair (i, j) is comparable
    if the patient with shorter observed time had an event.

    Parameters
    ----------
    patients : list of dict
        Patient records.
    time_field : str
        Key for survival time.
    event_field : str
        Key for event indicator.
    coefficients : dict
        Fitted model coefficients.
    covariate_fields : list of str
        Covariate field names.

    Returns
    -------
    float
        Concordance index between 0 and 1.
    """
    X, feature_names = _encode_covariates(patients, covariate_fields)
    n = len(patients)

    # Compute risk scores
    risk_scores = []
    for i in range(n):
        score = sum(
            X[i][j] * coefficients.get(feature_names[j], 0.0)
            for j in range(len(feature_names))
        )
        risk_scores.append(score)

    times = [float(p[time_field]) for p in patients]
    events = [int(p[event_field]) for p in patients]

    concordant = 0
    discordant = 0
    tied_risk = 0

    for i in range(n):
        for j in range(i + 1, n):
            # Only count comparable pairs
            if times[i] < times[j] and events[i] == 1:
                # Patient i had event first
                if risk_scores[i] > risk_scores[j]:
                    concordant += 1
                elif risk_scores[i] < risk_scores[j]:
                    discordant += 1
                else:
                    tied_risk += 1
            elif times[j] < times[i] and events[j] == 1:
                # Patient j had event first
                if risk_scores[j] > risk_scores[i]:
                    concordant += 1
                elif risk_scores[j] < risk_scores[i]:
                    discordant += 1
                else:
                    tied_risk += 1
            elif times[i] == times[j] and events[i] == 1 and events[j] == 1:
                # Both events at same time
                if risk_scores[i] == risk_scores[j]:
                    tied_risk += 1
                else:
                    concordant += 0.5
                    discordant += 0.5

    total = concordant + discordant + tied_risk
    if total == 0:
        return 0.5

    c_index = (concordant + 0.5 * tied_risk) / total
    return round(c_index, 10)


def compute_hazard_ratios(coefficients, standard_errors, confidence_level=0.95):
    """
    Compute hazard ratios and their confidence intervals from Cox model
    coefficients.

    HR = exp(beta), with CI = exp(beta +/- z * SE(beta))

    Parameters
    ----------
    coefficients : dict
        Model coefficients keyed by feature name.
    standard_errors : dict
        Standard errors keyed by feature name.
    confidence_level : float
        Confidence level for the interval.

    Returns
    -------
    list of dict
        Hazard ratio results for each covariate.
    """
    alpha = 1.0 - confidence_level
    z = _normal_quantile(1.0 - alpha / 2.0)

    results = []
    for feature in sorted(coefficients.keys()):
        beta = coefficients[feature]
        se = standard_errors.get(feature, 0.0)

        hr = math.exp(beta)
        ci_lower = math.exp(beta - z * se) if se > 0 else hr
        ci_upper = math.exp(beta + z * se) if se > 0 else hr

        results.append(
            {
                "feature": feature,
                "coefficient": round(beta, 6),
                "hazard_ratio": round(hr, 6),
                "ci_lower": round(ci_lower, 6),
                "ci_upper": round(ci_upper, 6),
                "se": round(se, 6),
                "z_score": round(beta / se, 6) if se > 0 else 0.0,
                "p_value": round(
                    2.0 * (1.0 - _normal_cdf(abs(beta / se))), 6
                ) if se > 0 else 1.0,
            }
        )

    return results


def _compute_likelihood_components(X, times, events, beta, n_features):
    """
    Compute the partial log-likelihood, gradient vector, and Hessian matrix
    for the Cox model using the Breslow approximation for tied events.

    For each event at time t_i:
        Contribution to log-likelihood: x_i'beta - log(sum_{j in R_i} exp(x_j'beta))

    The risk set R_i includes all patients with observed time >= t_i.
    Since data is sorted descending by time, we accumulate from the start.
    """
    n = len(times)
    log_likelihood = 0.0
    gradient = [0.0] * n_features
    hessian = [[0.0] * n_features for _ in range(n_features)]

    # Compute exp(x'beta) for all patients
    exp_xb = []
    for i in range(n):
        xb = sum(X[i][j] * beta[j] for j in range(n_features))
        exp_xb.append(math.exp(min(xb, 500)))  # Clip to prevent overflow

    # Accumulate risk set sums (data sorted descending by time)
    # In descending order, the risk set at time t_i includes indices 0..i
    # because those patients have time >= t_i
    risk_sum = 0.0
    risk_sum_x = [0.0] * n_features
    risk_sum_xx = [[0.0] * n_features for _ in range(n_features)]

    for i in range(n):
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
                    )

    return log_likelihood, gradient, hessian


def _encode_covariates(patients, covariate_fields):
    """
    Encode patient covariates into a numeric matrix.

    Numeric fields are used directly. String/categorical fields are
    encoded as binary indicators (dummy variables) for all but the
    first level (reference encoding).

    Returns
    -------
    tuple of (list of list, list of str)
        Feature matrix and feature names.
    """
    # Determine field types and categorical levels
    field_info = {}
    for field in covariate_fields:
        values = set()
        is_numeric = True
        for patient in patients:
            if field in patient:
                val = patient[field]
                if isinstance(val, str):
                    is_numeric = False
                    values.add(val)
                elif isinstance(val, (int, float)):
                    values.add(val)

        if is_numeric:
            field_info[field] = {"type": "numeric"}
        else:
            sorted_levels = sorted(values)
            # Reference encoding: skip first level
            field_info[field] = {
                "type": "categorical",
                "levels": sorted_levels[1:],
                "reference": sorted_levels[0] if sorted_levels else None,
            }

    # Build feature names
    feature_names = []
    for field in covariate_fields:
        info = field_info[field]
        if info["type"] == "numeric":
            feature_names.append(field)
        else:
            for level in info["levels"]:
                feature_names.append(f"{field}_{level}")

    # Encode matrix
    X = []
    for patient in patients:
        row = []
        for field in covariate_fields:
            info = field_info[field]
            if info["type"] == "numeric":
                val = patient.get(field, 0)
                row.append(float(val) if isinstance(val, (int, float)) else 0.0)
            else:
                val = patient.get(field, "")
                for level in info["levels"]:
                    row.append(1.0 if val == level else 0.0)
        X.append(row)

    return X, feature_names


def _solve_linear_system(hessian, gradient, n):
    """
    Solve H * delta = g using Gaussian elimination with partial pivoting.
    Returns delta (the Newton-Raphson step direction).
    """
    # Augment matrix [H | g]
    aug = [row[:] + [gradient[i]] for i, row in enumerate(hessian)]

    # Forward elimination
    for col in range(n):
        # Find pivot
        max_row = col
        max_val = abs(aug[col][col])
        for row in range(col + 1, n):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                max_row = row

        if max_val < 1e-15:
            return None

        # Swap rows
        aug[col], aug[max_row] = aug[max_row], aug[col]

        # Eliminate below
        for row in range(col + 1, n):
            factor = aug[row][col] / aug[col][col]
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]

    # Back substitution
    delta = [0.0] * n
    for i in range(n - 1, -1, -1):
        if abs(aug[i][i]) < 1e-15:
            delta[i] = 0.0
        else:
            delta[i] = aug[i][n]
            for j in range(i + 1, n):
                delta[i] -= aug[i][j] * delta[j]
            delta[i] /= aug[i][i]

    return delta


def _invert_matrix(matrix, n):
    """Invert a matrix using Gauss-Jordan elimination."""
    # Augment with identity
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)]
           for i, row in enumerate(matrix)]

    for col in range(n):
        # Find pivot
        max_row = col
        max_val = abs(aug[col][col])
        for row in range(col + 1, n):
            if abs(aug[row][col]) > max_val:
                max_val = abs(aug[row][col])
                max_row = row

        if max_val < 1e-15:
            return None

        aug[col], aug[max_row] = aug[max_row], aug[col]

        # Scale pivot row
        pivot = aug[col][col]
        for j in range(2 * n):
            aug[col][j] /= pivot

        # Eliminate other rows
        for row in range(n):
            if row != col:
                factor = aug[row][col]
                for j in range(2 * n):
                    aug[row][j] -= factor * aug[col][j]

    # Extract inverse
    return [row[n:] for row in aug]


def _normal_quantile(p):
    """Approximate inverse normal CDF."""
    if p <= 0:
        return -8.0
    if p >= 1:
        return 8.0
    if p == 0.5:
        return 0.0

    if p < 0.5:
        return -_rational_approx(math.sqrt(-2.0 * math.log(p)))
    else:
        return _rational_approx(math.sqrt(-2.0 * math.log(1.0 - p)))


def _rational_approx(t):
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308
    return t - (c0 + c1 * t + c2 * t ** 2) / (
        1.0 + d1 * t + d2 * t ** 2 + d3 * t ** 3
    )


def _normal_cdf(z):
    """Standard normal CDF (Abramowitz & Stegun approximation)."""
    if z < -8.0:
        return 0.0
    if z > 8.0:
        return 1.0

    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    sign = 1.0
    if z < 0:
        sign = -1.0
    z_abs = abs(z) / math.sqrt(2.0)

    t = 1.0 / (1.0 + p * z_abs)
    y = 1.0 - (
        ((((a5 * t + a4) * t) + a3) * t + a2) * t + a1
    ) * t * math.exp(-(z_abs ** 2))

    return 0.5 * (1.0 + sign * y)
