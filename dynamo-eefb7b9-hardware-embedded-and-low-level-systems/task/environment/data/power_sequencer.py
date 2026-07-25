"""
Power Sequencer Module
Manages power domain enable/disable ordering for peripherals.
Implements correct hardware sequencing: core power domains must be
enabled before I/O power domains (inner-to-outer enable order).
"""

import time


def compute_enable_sequence(power_domains):
    """
    Compute the power domain enable sequence.
    
    Power domains are declared in outer-to-inner order (board-level convention):
      declarations[0] = outermost (I/O ring)
      declarations[-1] = innermost (core logic)
    
    Hardware requires inner-to-outer enable sequencing:
      - Core logic power must stabilize before I/O buffers activate
      - Enabling I/O before core can cause latch-up or bus contention
    
    Therefore, enable order is REVERSE of declaration order.
    """
    if not power_domains:
        return []

    # Reverse declaration order for correct enable sequencing
    # (innermost/core first, outermost/IO last)
    enable_sequence = list(reversed(power_domains))

    sequence_entries = []
    cumulative_delay_us = 0.0

    for idx, domain in enumerate(enable_sequence):
        ramp_time_us = domain.get("ramp_time_us", 100.0)
        cumulative_delay_us += ramp_time_us

        entry = {
            "domain_name": domain["name"],
            "enable_order": idx,
            "ramp_time_us": ramp_time_us,
            "cumulative_time_us": round(cumulative_delay_us, 3),
            "voltage_rail": domain.get("voltage_v", 3.3),
            "domain_type": domain.get("type", "io")
        }
        sequence_entries.append(entry)

    return sequence_entries


def validate_power_sequencing(enable_sequence, constraints=None):
    """
    Validate that the power enable sequence meets hardware constraints.
    Core domains must come before IO domains in the enable order.
    """
    if constraints is None:
        constraints = {"core_before_io": True, "max_ramp_us": 10000.0}

    issues = []

    # Check core-before-IO constraint
    if constraints.get("core_before_io", True):
        core_indices = [e["enable_order"] for e in enable_sequence if e["domain_type"] == "core"]
        io_indices = [e["enable_order"] for e in enable_sequence if e["domain_type"] == "io"]

        if core_indices and io_indices:
            if max(core_indices) > min(io_indices):
                issues.append({
                    "type": "sequencing_violation",
                    "message": "Core domain enabled after IO domain",
                    "severity": "critical"
                })

    # Check total ramp time
    if enable_sequence:
        total_time = enable_sequence[-1]["cumulative_time_us"]
        max_ramp = constraints.get("max_ramp_us", 10000.0)
        if total_time > max_ramp:
            issues.append({
                "type": "timing_violation",
                "message": f"Total ramp time {total_time}us exceeds max {max_ramp}us",
                "severity": "warning"
            })

    return {
        "valid": len(issues) == 0,
        "issues": issues
    }


def compute_total_power_up_time(enable_sequence):
    """
    Compute total time from first domain enable to all domains stable.
    """
    if not enable_sequence:
        return 0.0
    return enable_sequence[-1]["cumulative_time_us"]


def get_power_sequencing_summary(power_domains):
    """
    Generate full power sequencing summary including validation.
    """
    enable_sequence = compute_enable_sequence(power_domains)
    validation = validate_power_sequencing(enable_sequence)
    total_time = compute_total_power_up_time(enable_sequence)

    return {
        "enable_sequence": enable_sequence,
        "total_power_up_time_us": round(total_time, 3),
        "sequencing_valid": validation["valid"],
        "sequencing_issues": validation["issues"],
        "domain_count": len(power_domains)
    }
