"""
Merge resolver for the Shell Environment Profile Compiler.
Merges variable definitions from multiple layers with priority-based
override semantics (higher priority layers override lower ones).
"""


def merge_layers(parsed_layers: list) -> dict:
    """
    Merge variables from all layers using priority ordering.
    Higher priority values override lower priority for the same variable.

    Args:
        parsed_layers: List of layer dicts with name, priority, variables.

    Returns:
        Dict of {var_name: {value, source, quote_style, multiline, priority}}.
    """
    # Sort by priority (lowest first, so highest overwrites)
    sorted_layers = sorted(parsed_layers, key=lambda l: l["priority"])

    merged = {}
    for layer in sorted_layers:
        layer_name = layer["name"]
        layer_priority = layer["priority"]

        for var_name, var_info in layer["variables"].items():
            merged[var_name] = {
                "value": var_info["value"],
                "source": layer_name,
                "quote_style": var_info.get("quote_style", "none"),
                "multiline": var_info.get("multiline", False),
                "priority": layer_priority,
            }

    return merged


def get_override_report(parsed_layers: list) -> dict:
    """
    Report which variables are overridden across layers.
    Returns dict of {var_name: [list of layer names defining it]}.
    """
    definitions = {}
    for layer in parsed_layers:
        for var_name in layer["variables"]:
            if var_name not in definitions:
                definitions[var_name] = []
            definitions[var_name].append(layer["name"])

    return {k: v for k, v in sorted(definitions.items()) if len(v) > 1}


def count_per_layer(parsed_layers: list) -> dict:
    """Count variables defined per layer."""
    return {layer["name"]: len(layer["variables"]) for layer in parsed_layers}
