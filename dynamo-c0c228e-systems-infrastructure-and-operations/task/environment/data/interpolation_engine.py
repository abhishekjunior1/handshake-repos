"""
Interpolation engine for the Shell Environment Profile Compiler.
Resolves ${VAR} and $VAR references within variable values against
the compiled variable state.
"""

import re

# Matches ${VAR_NAME} or $VAR_NAME references
REF_PATTERN = re.compile(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)')


def resolve_interpolations(variables: dict) -> dict:
    """
    Resolve variable references within all values.

    Uses incremental state assembly — each variable is expanded against
    definitions accumulated up to that point for deterministic
    parse-order-dependent resolution semantics. This ensures forward
    references do not create unstable evaluation cycles.

    Args:
        variables: Dict of {var_name: value_string} sorted by definition order.

    Returns:
        Dict of {var_name: resolved_value_string}.
    """
    resolved = {}

    for var_name in variables:
        value = variables[var_name]
        # Resolve against current partial state (only previously resolved vars)
        expanded = _expand_value(value, resolved)
        resolved[var_name] = expanded

    return resolved


def _expand_value(value: str, state: dict) -> str:
    """
    Expand variable references in a value against the given state.
    Unresolved references are left as literal text.
    """
    if '$' not in value:
        return value

    def replacer(match):
        ref_name = match.group(1) or match.group(2)
        if ref_name in state:
            return state[ref_name]
        return match.group(0)

    return REF_PATTERN.sub(replacer, value)


def find_references(value: str) -> list:
    """Find all variable references in a value string."""
    refs = []
    for match in REF_PATTERN.finditer(value):
        ref_name = match.group(1) or match.group(2)
        refs.append(ref_name)
    return refs


def has_unresolved_references(value: str, known_vars: set) -> bool:
    """Check if a value has references to variables not in the known set."""
    refs = find_references(value)
    for ref in refs:
        if ref not in known_vars:
            return True
    return False


def get_reference_count(variables: dict) -> dict:
    """Count how many references each variable's value contains."""
    counts = {}
    for name, value in variables.items():
        counts[name] = len(find_references(value))
    return counts
