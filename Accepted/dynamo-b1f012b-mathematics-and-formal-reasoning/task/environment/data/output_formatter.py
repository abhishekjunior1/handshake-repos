"""
Output formatter for polynomial GCD computation results.

Formats all computation results into a structured JSON format with
fields for input polynomials, GCD, resultant, factorization, and metadata.
"""

import json
from polynomial import degree, leading_coeff, strip_trailing_zeros


def format_polynomial(poly):
    """Format polynomial as a human-readable string."""
    poly = strip_trailing_zeros(poly)
    if poly == [0]:
        return "0"
    terms = []
    for i, c in enumerate(poly):
        if c == 0:
            continue
        if i == 0:
            terms.append(str(c))
        elif i == 1:
            if c == 1:
                terms.append("x")
            elif c == -1:
                terms.append("-x")
            else:
                terms.append(f"{c}*x")
        else:
            if c == 1:
                terms.append(f"x^{i}")
            elif c == -1:
                terms.append(f"-x^{i}")
            else:
                terms.append(f"{c}*x^{i}")
    return " + ".join(terms).replace(" + -", " - ") if terms else "0"


def format_results(input_f, input_g, gcd_result, resultant_value,
                   subresultant_degs, cofactor_resultant, factorization_info, metadata):
    """
    Format all computation results into structured JSON output.
    
    Args:
        input_f, input_g: input polynomial coefficients
        gcd_result: computed GCD polynomial coefficients
        resultant_value: integer resultant of f and g
        subresultant_degs: list of degrees in the subresultant PRS
        cofactor_resultant: resultant of f/gcd and g/gcd
        factorization_info: dict from factorization analysis
        metadata: computation metadata dict
        
    Returns:
        dict ready for JSON serialization
    """
    output = {
        "input_polynomials": {
            "f": {
                "coefficients": list(input_f),
                "degree": degree(input_f),
                "string": format_polynomial(input_f)
            },
            "g": {
                "coefficients": list(input_g),
                "degree": degree(input_g),
                "string": format_polynomial(input_g)
            }
        },
        "gcd": {
            "coefficients": list(gcd_result),
            "degree": degree(gcd_result),
            "leading_coefficient": leading_coeff(gcd_result),
            "string": format_polynomial(gcd_result),
            "verified": metadata.get("division_verified", False)
        },
        "resultant": {
            "value": resultant_value,
            "subresultant_degrees": subresultant_degs,
            "is_zero": resultant_value == 0,
            "cofactor_resultant": cofactor_resultant
        },
        "factorization": {
            "content_f": factorization_info.get("content_f", 1),
            "content_g": factorization_info.get("content_g", 1),
            "content_gcd": factorization_info.get("content_gcd", 1),
            "primitive_gcd": factorization_info.get("primitive_gcd", [1]),
            "square_free_gcd": factorization_info.get("square_free_gcd", []),
            "coprime": factorization_info.get("coprime", True)
        },
        "computation_metadata": metadata
    }
    
    return output


def write_output(output_dict, filepath):
    """Write formatted output to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(output_dict, f, indent=2)
    return filepath
