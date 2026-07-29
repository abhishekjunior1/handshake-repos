"""
Preprocessor module for the survival analysis pipeline.

Handles event classification, covariate standardization, and
construction of time tables (ordered event/censoring time lists
with at-risk counts) needed by the Kaplan-Meier and log-rank
procedures.
"""

import math


def classify_events(patients, time_field, event_field):
    """
    Classify each patient record with internal event markers.

    Adds '_event_observed' (bool) and '_survival_time' (float) fields
    to each patient dictionary for downstream processing.

    Parameters
    ----------
    patients : list of dict
        Raw patient records.
    time_field : str
        Key for the survival/follow-up time.
    event_field : str
        Key for the event indicator (1=event, 0=censored).

    Returns
    -------
    list of dict
        Patient records augmented with internal classification fields.
    """
    classified = []
    for patient in patients:
        record = dict(patient)
        record["_survival_time"] = float(patient[time_field])
        record["_event_observed"] = patient[event_field] == 1
        classified.append(record)

    return classified


def standardize_covariates(patients, covariate_fields):
    """
    Standardize numeric covariates to zero mean and unit variance.

    Non-numeric covariates are converted to indicator (dummy) variables.
    This is required for stable Cox model fitting.

    Parameters
    ----------
    patients : list of dict
        Classified patient records.
    covariate_fields : list of str
        Names of covariate fields to standardize.

    Returns
    -------
    dict
        Dictionary with 'means', 'stds', and 'standardized_patients' keys.
    """
    if not covariate_fields:
        return {"means": {}, "stds": {}, "standardized_patients": patients}

    # Compute means and stds for numeric covariates
    means = {}
    stds = {}
    numeric_fields = []

    for field in covariate_fields:
        values = []
        for patient in patients:
            if field in patient:
                val = patient[field]
                if isinstance(val, (int, float)):
                    values.append(float(val))

        if values:
            numeric_fields.append(field)
            n = len(values)
            mean = sum(values) / n
            variance = sum((x - mean) ** 2 for x in values) / (n - 1) if n > 1 else 0.0
            means[field] = mean
            stds[field] = math.sqrt(variance) if variance > 0 else 1.0

    # Apply standardization
    standardized = []
    for patient in patients:
        record = dict(patient)
        for field in numeric_fields:
            if field in record and isinstance(record[field], (int, float)):
                record[field] = (float(record[field]) - means[field]) / stds[field]
        standardized.append(record)

    return {
        "means": means,
        "stds": stds,
        "standardized_patients": standardized,
    }


def build_time_table(patients, time_field, event_field):
    """
    Construct an ordered time table from patient records.

    The time table lists each unique time point with the number of events,
    number of censorings, and the size of the at-risk set at that time.

    At each time point t:
    - at_risk = number of patients with survival time >= t
    - events = number of patients with survival time == t and event == 1
    - censored = number of patients with survival time == t and event == 0

    Parameters
    ----------
    patients : list of dict
        Patient records (classified).
    time_field : str
        Key for survival time.
    event_field : str
        Key for event indicator.

    Returns
    -------
    list of dict
        Ordered time table entries with 'time', 'at_risk', 'events',
        'censored' fields.
    """
    # Collect all unique time points and their events/censorings
    time_data = {}
    for patient in patients:
        t = float(patient[time_field])
        event = patient[event_field]

        if t not in time_data:
            time_data[t] = {"events": 0, "censored": 0}

        if event == 1:
            time_data[t]["events"] += 1
        else:
            time_data[t]["censored"] += 1

    # Sort time points
    sorted_times = sorted(time_data.keys())

    # Build time table with at-risk counts
    n_total = len(patients)
    at_risk = n_total
    time_table = []

    for t in sorted_times:
        entry = {
            "time": t,
            "at_risk": at_risk,
            "events": time_data[t]["events"],
            "censored": time_data[t]["censored"],
        }
        time_table.append(entry)

        # Remove events and censored from risk set
        at_risk -= time_data[t]["events"] + time_data[t]["censored"]

    return time_table


def compute_follow_up_statistics(patients, time_field, event_field):
    """
    Compute descriptive statistics of follow-up time.

    Parameters
    ----------
    patients : list of dict
        Patient records.
    time_field : str
        Key for survival time.
    event_field : str
        Key for event indicator.

    Returns
    -------
    dict
        Statistics including median follow-up, total person-time,
        event rate, and censoring proportion.
    """
    times = [float(p[time_field]) for p in patients]
    events = [p[event_field] for p in patients]

    n = len(times)
    total_time = sum(times)
    n_events = sum(events)
    n_censored = n - n_events

    sorted_times = sorted(times)
    if n % 2 == 0:
        median_time = (sorted_times[n // 2 - 1] + sorted_times[n // 2]) / 2.0
    else:
        median_time = sorted_times[n // 2]

    return {
        "n_patients": n,
        "n_events": n_events,
        "n_censored": n_censored,
        "censoring_proportion": round(n_censored / n, 6) if n > 0 else 0.0,
        "total_person_time": round(total_time, 6),
        "median_follow_up": round(median_time, 6),
        "event_rate": round(n_events / total_time, 6) if total_time > 0 else 0.0,
    }
