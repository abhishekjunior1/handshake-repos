from config import (
    CATEGORY_MULTIPLIERS,
    REGION_TAX_RATES,
    PRIORITY_WEIGHTS,
    LATE_ARRIVAL_THRESHOLD_DAYS,
    parse_timestamp,
    is_late_arrival,
)


def compute_adjusted_amount(record):
    amount = record.get("amount", 0)
    category = record.get("category", "")
    region = record.get("region", "")

    multiplier = CATEGORY_MULTIPLIERS.get(category, 1.0)
    tax_rate = REGION_TAX_RATES.get(region, 0.0)

    base_adjusted = amount * multiplier
    tax_amount = base_adjusted * tax_rate
    return round(base_adjusted + tax_amount, 2)


def compute_priority_score(record):
    priority = record.get("priority", "medium")
    base_weight = PRIORITY_WEIGHTS.get(priority, 2)

    amount = record.get("amount", 0)
    amount_factor = min(amount / 1000.0, 5.0)

    score = base_weight * (1 + amount_factor * 0.1)
    return round(score, 4)


def detect_scd_type(record):
    if record.get("scd_type") is not None:
        return record["scd_type"]
    effective_date = record.get("effective_date")
    timestamp = record.get("timestamp")
    if effective_date is not None and effective_date != timestamp:
        return 2
    return 1


def compute_temporal_flags(record):
    timestamp = parse_timestamp(record.get("timestamp"))
    effective_date = parse_timestamp(record.get("effective_date"))

    flags = {
        "is_late": False,
        "temporal_offset_days": 0,
    }

    if timestamp is not None and effective_date is not None:
        offset = (timestamp - effective_date).days
        flags["temporal_offset_days"] = offset
        flags["is_late"] = abs(offset) > LATE_ARRIVAL_THRESHOLD_DAYS

    return flags


def derive_composite_key(record):
    parts = [
        record.get("category", "unknown"),
        record.get("region", "unknown"),
        record.get("priority", "medium"),
    ]
    return "_".join(parts)


def apply_status_weight(record):
    status = record.get("status", "pending")
    weights = {
        "active": 1.0,
        "pending": 0.8,
        "completed": 1.2,
        "cancelled": 0.0,
    }
    return weights.get(status, 1.0)


def transform_single(record):
    transformed = dict(record)

    transformed["adjusted_amount"] = compute_adjusted_amount(record)
    transformed["priority_score"] = compute_priority_score(record)
    transformed["scd_type"] = detect_scd_type(record)
    transformed["composite_key"] = derive_composite_key(record)

    temporal_flags = compute_temporal_flags(record)
    transformed["is_late"] = temporal_flags["is_late"]
    transformed["temporal_offset_days"] = temporal_flags["temporal_offset_days"]

    status_weight = apply_status_weight(record)
    if status_weight == 0.0:
        transformed["adjusted_amount"] = 0.0

    return transformed


def transform_records(records):
    transformed = []
    for record in records:
        result = transform_single(record)
        transformed.append(result)
    return transformed
