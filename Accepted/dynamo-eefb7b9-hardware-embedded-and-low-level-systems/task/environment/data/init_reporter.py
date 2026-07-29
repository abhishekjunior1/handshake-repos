"""
Init Reporter Module
Formats the peripheral initialization pipeline results into
structured JSON output for verification and logging.
"""

import json


def format_output(pipeline_results):
    """
    Format all pipeline stage results into the final output structure.
    """
    output = {
        "initialization_summary": build_summary(pipeline_results),
        "clock_configuration": pipeline_results.get("clock_summary", {}),
        "power_sequencing": pipeline_results.get("power_summary", {}),
        "bus_transactions": pipeline_results.get("bus_transactions", {}),
        "register_programming": pipeline_results.get("register_summary", {}),
        "device_enumeration": pipeline_results.get("enumeration_summary", {}),
        "diagnostics": build_diagnostics(pipeline_results)
    }
    return output


def build_summary(pipeline_results):
    """
    Build top-level initialization summary from all stage results.
    """
    clock = pipeline_results.get("clock_summary", {})
    power = pipeline_results.get("power_summary", {})
    reg = pipeline_results.get("register_summary", {})
    enum_result = pipeline_results.get("enumeration_summary", {})

    total_time_us = (
        clock.get("pll_lock_time_us", 0.0) +
        power.get("total_power_up_time_us", 0.0) +
        pipeline_results.get("programming_time_us", 0.0)
    )

    all_success = (
        reg.get("all_devices_successful", False) and
        enum_result.get("enumeration_complete", False) and
        power.get("sequencing_valid", True)
    )

    return {
        "total_init_time_us": round(total_time_us, 3),
        "all_peripherals_initialized": all_success,
        "devices_programmed": reg.get("total_registers_programmed", 0),
        "devices_lost": reg.get("total_registers_lost", 0),
        "devices_enumerated": enum_result.get("devices_identified", 0),
        "power_domains_enabled": power.get("domain_count", 0),
        "bus_protocol": pipeline_results.get("bus_protocol", "unknown")
    }


def build_diagnostics(pipeline_results):
    """
    Collect diagnostic information from all pipeline stages.
    """
    diag = {
        "clock_stable_at_programming": pipeline_results.get("clock_stable_at_programming", False),
        "peripheral_clock_mhz": pipeline_results.get("peripheral_clock_mhz", 0.0),
        "bus_contention_detected": len(pipeline_results.get("bus_issues", [])) > 0,
        "bus_issues": pipeline_results.get("bus_issues", []),
        "cs_sequence": pipeline_results.get("cs_sequence", [])
    }
    return diag


def write_output(output, output_path):
    """
    Write formatted output to JSON file.
    """
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
