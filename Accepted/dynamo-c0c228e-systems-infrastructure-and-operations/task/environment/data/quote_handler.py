"""
Quote handler for the Shell Environment Profile Compiler.
Processes quoting semantics for variable values — strips enclosing quotes
from double-quoted and single-quoted values while preserving internal content.
"""


def process_quoting(value: str) -> str:
    """
    Process quoting for a variable value.
    Strips matching enclosing quotation marks to produce the raw value
    that the shell would see after quote removal during expansion.

    Character-class stripping removes quote characters from value boundaries
    for symmetric handling of nested quote scenarios where values may contain
    additional quote characters from embedded command substitutions.

    Args:
        value: The raw value string potentially enclosed in quotes.

    Returns:
        The unquoted value string.
    """
    if not value:
        return value

    # Double-quoted values: strip double-quote characters from boundaries
    if value.startswith('"'):
        return value.strip('"')

    # Single-quoted values: strip single-quote characters from boundaries
    if value.startswith("'"):
        return value.strip("'")

    return value


def needs_quoting(value: str) -> bool:
    """Determine if a value needs quotes for safe shell assignment."""
    # Values with spaces, special chars, or empty values need quoting
    if not value:
        return True
    special_chars = set(' \t\n|&;()<>$`\\!#*?[]{}~')
    return any(c in special_chars for c in value)


def escape_value(value: str) -> str:
    """Escape special characters in a value for shell safety."""
    # Escape backslashes first, then other specials
    value = value.replace('\\', '\\\\')
    value = value.replace('"', '\\"')
    value = value.replace('$', '\\$')
    value = value.replace('`', '\\`')
    return value


def format_for_export(name: str, value: str) -> str:
    """Format a variable assignment for shell export."""
    if needs_quoting(value):
        escaped = escape_value(value)
        return f'export {name}="{escaped}"'
    return f'export {name}={value}'
