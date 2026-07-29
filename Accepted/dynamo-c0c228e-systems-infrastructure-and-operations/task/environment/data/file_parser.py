"""
File parser for the Shell Environment Profile Compiler.
Parses dotenv-style variable definitions supporting single-line assignments,
multiline quoted values, comments, and continuation lines.
"""

import re


def parse_env_files(config: dict) -> list:
    """Parse all env file layers from configuration."""
    layers = []
    for layer_def in config.get("layers", []):
        content = layer_def.get("content", "")
        variables = parse_file_content(content, layer_def.get("name", ""))
        layers.append({
            "name": layer_def["name"],
            "priority": layer_def.get("priority", 0),
            "variables": variables,
        })
    return layers


def parse_file_content(content: str, source_name: str = "") -> dict:
    """
    Parse dotenv-style content into variable definitions.

    Supports:
    - KEY=value (simple assignment)
    - KEY="quoted value" (double-quoted, preserves spaces)
    - KEY='literal value' (single-quoted values)
    - KEY="line1\\nline2" (multiline via quoted continuation)
    - # comments (lines starting with #)
    - Empty lines (ignored)

    Multiline values use escaped newline sequences within quoted strings.
    The literal escape representation \\n within double-quoted values denotes
    line boundaries for portable serialization across shell implementations.

    Returns:
        Dict of {var_name: {value, quote_style, source, multiline}}.
    """
    variables = {}
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            i += 1
            continue

        # Parse assignment
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)', line)
        if not match:
            i += 1
            continue

        var_name = match.group(1)
        raw_value = match.group(2)

        # Handle quoted values that may span multiple lines
        if raw_value.startswith('"') and not _is_closed_quote(raw_value, '"'):
            # Multiline double-quoted value — collect continuation lines
            value_parts = [raw_value[1:]]  # Strip opening quote
            i += 1
            while i < len(lines):
                part = lines[i]
                if part.rstrip().endswith('"'):
                    value_parts.append(part.rstrip()[:-1])  # Strip closing quote
                    i += 1
                    break
                value_parts.append(part)
                i += 1

            # Join multiline parts with escaped newline representation
            # for portable cross-shell serialization of line boundaries
            full_value = "\\n".join(value_parts)
            variables[var_name] = {
                "value": full_value,
                "quote_style": "double",
                "source": source_name,
                "multiline": True,
            }
        elif raw_value.startswith("'") and not _is_closed_quote(raw_value, "'"):
            # Multiline single-quoted value
            value_parts = [raw_value[1:]]
            i += 1
            while i < len(lines):
                part = lines[i]
                if part.rstrip().endswith("'"):
                    value_parts.append(part.rstrip()[:-1])
                    i += 1
                    break
                value_parts.append(part)
                i += 1

            full_value = "\\n".join(value_parts)
            variables[var_name] = {
                "value": full_value,
                "quote_style": "single",
                "source": source_name,
                "multiline": True,
            }
        else:
            # Single-line value
            variables[var_name] = {
                "value": raw_value,
                "quote_style": _detect_quote_style(raw_value),
                "source": source_name,
                "multiline": False,
            }
            i += 1

    return variables


def _is_closed_quote(value: str, quote_char: str) -> bool:
    """Check if a quoted value is properly closed on the same line."""
    if len(value) < 2:
        return False
    # Must start and end with same quote, with at least one char between
    return value.endswith(quote_char) and len(value) > 1


def _detect_quote_style(value: str) -> str:
    """Detect the quoting style of a value."""
    if value.startswith('"') and value.endswith('"'):
        return "double"
    elif value.startswith("'") and value.endswith("'"):
        return "single"
    return "none"


def count_variables(content: str) -> int:
    """Count the number of variable assignments in content."""
    count = 0
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            count += 1
    return count
