from config import (
    REQUIRED_FIELDS,
    OPTIONAL_FIELDS,
    VALID_STATUSES,
    PRIORITY_WEIGHTS,
    CATEGORY_MULTIPLIERS,
    REGION_TAX_RATES,
    parse_timestamp,
)


class ValidationError:
    def __init__(self, record_id, field, reason):
        self.record_id = record_id
        self.field = field
        self.reason = reason

    def to_dict(self):
        return {
            "record_id": self.record_id,
            "field": self.field,
            "reason": self.reason,
        }


def validate_required_fields(record):
    errors = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            errors.append(
                ValidationError(record.get("id", "unknown"), field, "missing_required")
            )
    return errors


def validate_types(record):
    errors = []
    record_id = record.get("id", "unknown")

    if "amount" in record and record["amount"] is not None:
        try:
            float(record["amount"])
        except (ValueError, TypeError):
            errors.append(ValidationError(record_id, "amount", "invalid_numeric"))

    if "timestamp" in record and record["timestamp"] is not None:
        if parse_timestamp(record["timestamp"]) is None:
            errors.append(ValidationError(record_id, "timestamp", "invalid_datetime"))

    if "effective_date" in record and record["effective_date"] is not None:
        if parse_timestamp(record["effective_date"]) is None:
            errors.append(
                ValidationError(record_id, "effective_date", "invalid_datetime")
            )

    return errors


def validate_domain_values(record):
    errors = []
    record_id = record.get("id", "unknown")

    if "category" in record and record["category"] is not None:
        if record["category"] not in CATEGORY_MULTIPLIERS:
            errors.append(ValidationError(record_id, "category", "invalid_category"))

    if "region" in record and record["region"] is not None:
        if record["region"] not in REGION_TAX_RATES:
            errors.append(ValidationError(record_id, "region", "invalid_region"))

    if "status" in record and record["status"] is not None:
        if record["status"] not in VALID_STATUSES:
            errors.append(ValidationError(record_id, "status", "invalid_status"))

    if "priority" in record and record["priority"] is not None:
        if record["priority"] not in PRIORITY_WEIGHTS:
            errors.append(ValidationError(record_id, "priority", "invalid_priority"))

    return errors


def normalize_record(record):
    normalized = {}
    for field in REQUIRED_FIELDS + OPTIONAL_FIELDS:
        value = record.get(field)
        if isinstance(value, str):
            value = value.strip().lower() if field != "id" else value.strip()
        normalized[field] = value

    if normalized.get("amount") is not None:
        normalized["amount"] = round(float(normalized["amount"]), 2)

    if normalized.get("scd_type") is not None:
        normalized["scd_type"] = int(normalized["scd_type"])

    if normalized.get("status") is None:
        normalized["status"] = "pending"

    if normalized.get("priority") is None:
        normalized["priority"] = "medium"

    return normalized


def validate_and_normalize(records):
    valid = []
    rejected = []

    for record in records:
        errors = []
        errors.extend(validate_required_fields(record))
        errors.extend(validate_types(record))

        if errors:
            rejected.append({
                "record": record,
                "errors": [e.to_dict() for e in errors],
            })
            continue

        domain_errors = validate_domain_values(record)
        if domain_errors:
            rejected.append({
                "record": record,
                "errors": [e.to_dict() for e in domain_errors],
            })
            continue

        normalized = normalize_record(record)
        valid.append(normalized)

    return valid, rejected
