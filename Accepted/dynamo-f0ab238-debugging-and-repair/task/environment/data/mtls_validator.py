"""Mutual TLS policy validation for service mesh traffic."""

from typing import Any


# mTLS enforcement modes
MTLS_DISABLED = "disabled"
MTLS_PERMISSIVE = "permissive"
MTLS_STRICT = "strict"

# Validation result codes
VALIDATION_PASS = "pass"
VALIDATION_FAIL = "fail"
VALIDATION_SKIP = "skip"


def validate_mtls_policy(
    source_service: dict,
    destination_service: dict,
    global_mtls_mode: str,
    routing_rule: dict
) -> dict:
    """
    Validate mTLS requirements between source and destination services.

    In strict mode, both services must have mtls_required=True.
    In permissive mode, the connection proceeds but is flagged if one side lacks mTLS.
    In disabled mode, mTLS validation is skipped entirely.

    Returns a validation result dict with status and details.
    """
    result = {
        "source_service": source_service["service_id"],
        "destination_service": destination_service["service_id"],
        "global_mode": global_mtls_mode,
        "validation_status": VALIDATION_SKIP,
        "mtls_enforced": False,
        "policy_violations": [],
        "effective_tls_mode": "plaintext"
    }

    if global_mtls_mode == MTLS_DISABLED:
        result["validation_status"] = VALIDATION_SKIP
        result["effective_tls_mode"] = "plaintext"
        return result

    source_requires = source_service.get("mtls_required", False)
    dest_requires = destination_service.get("mtls_required", False)

    if global_mtls_mode == MTLS_STRICT:
        if not source_requires:
            result["policy_violations"].append(
                f"source '{source_service['service_id']}' lacks mTLS in strict mode"
            )
        if not dest_requires:
            result["policy_violations"].append(
                f"destination '{destination_service['service_id']}' lacks mTLS in strict mode"
            )

        if result["policy_violations"]:
            result["validation_status"] = VALIDATION_FAIL
            result["mtls_enforced"] = False
            result["effective_tls_mode"] = "rejected"
        else:
            result["validation_status"] = VALIDATION_PASS
            result["mtls_enforced"] = True
            result["effective_tls_mode"] = "mutual_tls"

    elif global_mtls_mode == MTLS_PERMISSIVE:
        if source_requires and dest_requires:
            result["validation_status"] = VALIDATION_PASS
            result["mtls_enforced"] = True
            result["effective_tls_mode"] = "mutual_tls"
        elif source_requires or dest_requires:
            result["validation_status"] = VALIDATION_PASS
            result["mtls_enforced"] = False
            result["effective_tls_mode"] = "tls_one_way"
            result["policy_violations"].append(
                "asymmetric mTLS configuration in permissive mode"
            )
        else:
            result["validation_status"] = VALIDATION_PASS
            result["mtls_enforced"] = False
            result["effective_tls_mode"] = "plaintext"

    return result


def check_certificate_compatibility(
    source_namespace: str,
    dest_namespace: str,
    mtls_enforced: bool
) -> dict:
    """
    Check certificate trust chain compatibility between namespaces.

    When mTLS is enforced, services in the same namespace share a trust domain.
    Cross-namespace communication requires intermediate CA validation.
    """
    compatibility = {
        "same_trust_domain": source_namespace == dest_namespace,
        "requires_intermediate_ca": source_namespace != dest_namespace and mtls_enforced,
        "certificate_status": "valid"
    }

    if not mtls_enforced:
        compatibility["certificate_status"] = "not_applicable"
    elif compatibility["same_trust_domain"]:
        compatibility["certificate_status"] = "valid"
    else:
        compatibility["certificate_status"] = "cross_domain_valid"

    return compatibility


def compute_tls_overhead_ms(
    protocol: str,
    mtls_enforced: bool,
    same_trust_domain: bool
) -> float:
    """
    Compute estimated TLS handshake overhead in milliseconds.

    mTLS adds overhead for mutual certificate exchange.
    Cross-domain adds additional overhead for CA chain validation.
    gRPC uses connection pooling, reducing per-request TLS overhead.
    """
    if not mtls_enforced:
        return 0.0

    base_overhead = 2.5  # Base TLS handshake cost

    if protocol == "gRPC":
        base_overhead *= 0.3  # Connection pooling amortization

    if mtls_enforced:
        base_overhead += 1.5  # Mutual certificate exchange

    if not same_trust_domain:
        base_overhead += 0.8  # CA chain validation

    return round(base_overhead, 3)
