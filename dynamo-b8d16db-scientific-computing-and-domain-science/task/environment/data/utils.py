"""
Shared utility functions for the adaptive quadrature integration pipeline.
Provides function evaluation, interval management, and convergence tracking.
"""

import math
import json


def evaluate_function(func_spec, x):
    """
    Evaluate a mathematical function defined by its specification at point x.
    
    Supports polynomial, trigonometric, exponential, and composite functions.
    Function spec format:
      {"type": "polynomial", "coefficients": [a0, a1, ..., an]}
      {"type": "exponential", "base": b, "scale": s}
      {"type": "trigonometric", "function": "sin"|"cos", "frequency": f, "amplitude": a}
      {"type": "composite", "terms": [spec1, spec2, ...], "operation": "multiply"|"add"}
      {"type": "power", "exponent": alpha, "scale": s}
    """
    func_type = func_spec["type"]
    
    if func_type == "polynomial":
        coeffs = func_spec["coefficients"]
        result = 0.0
        for i, c in enumerate(coeffs):
            result += c * (x ** i)
        return result
    
    elif func_type == "exponential":
        base = func_spec.get("base", math.e)
        scale = func_spec.get("scale", 1.0)
        return scale * (base ** x)
    
    elif func_type == "trigonometric":
        func_name = func_spec["function"]
        freq = func_spec.get("frequency", 1.0)
        amplitude = func_spec.get("amplitude", 1.0)
        phase = func_spec.get("phase", 0.0)
        if func_name == "sin":
            return amplitude * math.sin(freq * x + phase)
        elif func_name == "cos":
            return amplitude * math.cos(freq * x + phase)
        else:
            raise ValueError(f"Unknown trig function: {func_name}")
    
    elif func_type == "composite":
        terms = func_spec["terms"]
        operation = func_spec.get("operation", "add")
        values = [evaluate_function(term, x) for term in terms]
        if operation == "multiply":
            result = 1.0
            for v in values:
                result *= v
            return result
        elif operation == "add":
            return sum(values)
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    elif func_type == "power":
        exponent = func_spec["exponent"]
        scale = func_spec.get("scale", 1.0)
        offset = func_spec.get("offset", 0.0)
        if x + offset <= 0 and exponent < 0:
            return float('inf')
        return scale * ((x + offset) ** exponent)
    
    else:
        raise ValueError(f"Unknown function type: {func_type}")


def compute_interval_width(a, b):
    """Compute the width of interval [a, b]."""
    return abs(b - a)


def compute_interval_midpoint(a, b):
    """Compute the midpoint of interval [a, b]."""
    return (a + b) / 2.0


def generate_quadrature_nodes(a, b, n_points):
    """
    Generate equally-spaced quadrature nodes on [a, b].
    Returns n_points nodes including endpoints.
    """
    if n_points < 2:
        raise ValueError("Need at least 2 points")
    h = (b - a) / (n_points - 1)
    return [a + i * h for i in range(n_points)]


def compute_function_values(func_spec, nodes):
    """Evaluate function at all nodes."""
    return [evaluate_function(func_spec, x) for x in nodes]


def detect_singularity(func_spec, a, b, n_samples=10):
    """
    Detect potential singularities near endpoints by sampling function growth.
    Returns singularity info dict or None if no singularity detected.
    """
    h = (b - a) / n_samples
    
    # Check left endpoint
    left_values = []
    for i in range(1, n_samples // 2 + 1):
        x = a + i * h * 0.1
        try:
            val = evaluate_function(func_spec, x)
            if math.isfinite(val):
                left_values.append((x - a, abs(val)))
        except (ValueError, OverflowError):
            pass
    
    # Check right endpoint
    right_values = []
    for i in range(1, n_samples // 2 + 1):
        x = b - i * h * 0.1
        try:
            val = evaluate_function(func_spec, x)
            if math.isfinite(val):
                right_values.append((b - x, abs(val)))
        except (ValueError, OverflowError):
            pass
    
    singularity_info = None
    
    # Estimate singularity strength from growth rate
    if len(left_values) >= 3:
        distances = [v[0] for v in left_values]
        magnitudes = [v[1] for v in left_values]
        if magnitudes[0] > 0 and magnitudes[-1] > 0:
            log_ratio = math.log(magnitudes[0] / magnitudes[-1])
            dist_ratio = math.log(distances[0] / distances[-1])
            if abs(dist_ratio) > 1e-10:
                strength = -log_ratio / dist_ratio
                if strength > 0.1:
                    singularity_info = {
                        "endpoint": "left",
                        "strength": strength,
                        "location": a
                    }
    
    if len(right_values) >= 3:
        distances = [v[0] for v in right_values]
        magnitudes = [v[1] for v in right_values]
        if magnitudes[0] > 0 and magnitudes[-1] > 0:
            log_ratio = math.log(magnitudes[0] / magnitudes[-1])
            dist_ratio = math.log(distances[0] / distances[-1])
            if abs(dist_ratio) > 1e-10:
                strength = -log_ratio / dist_ratio
                if strength > 0.1:
                    if singularity_info is None or strength > singularity_info["strength"]:
                        singularity_info = {
                            "endpoint": "right",
                            "strength": strength,
                            "location": b
                        }
    
    return singularity_info


def format_result(integral_value, error_estimate, subdivisions, convergence_order,
                  singularity_strength, method_info):
    """Format the integration result as a standardized output dictionary."""
    return {
        "integral_value": round(integral_value, 12),
        "error_estimate": round(error_estimate, 12),
        "subdivisions": subdivisions,
        "convergence_order": round(convergence_order, 6),
        "singularity_strength": round(singularity_strength, 6) if singularity_strength else 0.0,
        "method_info": method_info
    }


def load_input(filepath):
    """Load input configuration from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def save_output(result, filepath):
    """Save result to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(result, f, indent=2)
