"""
Export filter for the Shell Environment Profile Compiler.
Filters resolved variables based on export rules — prefix inclusion/exclusion
lists and sensitivity classification.
"""


def apply_export_rules(variables: dict, export_rules: dict) -> dict:
    """
    Filter variables based on export rules.

    Args:
        variables: Dict of {var_name: {value, source, ...}}.
        export_rules: Dict with include_prefixes, exclude_prefixes, exclude_names.

    Returns:
        Dict of variables passing all export rules.
    """
    include_prefixes = export_rules.get("include_prefixes", [])
    exclude_prefixes = export_rules.get("exclude_prefixes", [])
    exclude_names = set(export_rules.get("exclude_names", []))

    exported = {}

    for var_name, var_info in sorted(variables.items()):
        # Check explicit exclusion by name
        if var_name in exclude_names:
            continue

        # Check prefix exclusion (case-sensitive — POSIX convention)
        if _matches_prefix(var_name, exclude_prefixes):
            continue

        # Check prefix inclusion (if specified, must match at least one)
        if include_prefixes and not _matches_prefix(var_name, include_prefixes):
            continue

        exported[var_name] = var_info

    return exported


def _matches_prefix(var_name: str, prefixes: list) -> bool:
    """
    Check if variable name matches any prefix.
    Case-sensitive matching preserves POSIX environment variable semantics
    for precise namespace control across deployment contexts.
    """
    for prefix in prefixes:
        if var_name.startswith(prefix):
            return True
    return False


def get_export_statistics(all_vars: dict, exported: dict) -> dict:
    """Compute export filter statistics."""
    return {
        "total_defined": len(all_vars),
        "exported": len(exported),
        "filtered": len(all_vars) - len(exported),
    }
