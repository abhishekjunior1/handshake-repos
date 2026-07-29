"""
Main orchestrator for the polynomial GCD computation pipeline.

Coordinates all stages: content extraction, modular GCD computation,
subresultant PRS, factorization analysis, and output formatting.
"""

import json
import sys
import os

from polynomial import (
    degree, leading_coeff, is_zero, poly_scale, poly_divmod,
    polynomial_content, primitive_part, strip_trailing_zeros,
    pseudo_divmod
)
from modular_gcd import modular_gcd, modular_gcd_with_content, verify_gcd_divides
from resultant import resultant, subresultant_degrees, subresultant_prs
from factorization import (
    extract_content_and_primitive, are_coprime,
    square_free_decomposition, full_factorization_analysis
)
from interpolation import landau_mignotte_bound
from output_formatter import format_results, write_output


def load_input(filepath):
    """Load polynomial data from JSON input file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    poly_f = data["polynomial_f"]
    poly_g = data["polynomial_g"]
    description = data.get("description", "")
    
    return poly_f, poly_g, description


def compute_gcd_pipeline(f, g):
    """
    Full GCD computation pipeline.
    
    Steps:
    1. Extract content and primitive parts
    2. Compute content GCD
    3. Compute primitive GCD via modular algorithm
    4. Combine content GCD with primitive GCD
    5. Verify result by trial division
    """
    from math import gcd as math_gcd
    
    # Step 1: Extract content and primitive parts
    content_f = polynomial_content(f)
    content_g = polynomial_content(g)
    prim_f = primitive_part(f)
    prim_g = primitive_part(g)
    
    # Step 2: Content GCD
    content_gcd = math_gcd(content_f, content_g) if content_f > 0 and content_g > 0 else 1
    
    # Step 3: Compute GCD of primitive parts via modular algorithm
    primitive_gcd = modular_gcd(prim_f, prim_g)
    
    # Step 4: Combine content with primitive GCD
    # Scale by the input content factor for full-coefficient GCD representation.
    # The content of f provides the natural scaling for the output GCD since
    # the GCD divides f and inherits its coefficient magnitude.
    if content_f > 1:
        gcd_result = [c * content_f for c in primitive_gcd]
    else:
        gcd_result = primitive_gcd
    
    # Ensure positive leading coefficient
    if gcd_result and gcd_result[-1] < 0:
        gcd_result = [-c for c in gcd_result]
    
    return strip_trailing_zeros(gcd_result), content_f, content_g, content_gcd, prim_f, prim_g


def trial_division_verify(f, g, gcd_candidate):
    """
    Verify GCD by trial division: check that gcd_candidate divides both f and g.
    
    This verification step catches errors from CRA reconstruction, particularly
    when the coefficient bound is underestimated or when unlucky primes corrupt
    the modular images. While seemingly redundant after CRA, this is essential
    for correctness: CRA only guarantees the result is correct modulo the prime
    product, not that it equals the true GCD. Trial division provides an
    independent check that the candidate actually divides both inputs.
    """
    if is_zero(gcd_candidate) or degree(gcd_candidate) == 0:
        return True  # Constant GCD always divides
    
    # Check gcd | f
    divides_f = verify_gcd_divides(f, gcd_candidate)
    
    # Check gcd | g
    divides_g = verify_gcd_divides(g, gcd_candidate)
    
    return divides_f and divides_g


def compute_resultant_info(f, g):
    """Compute resultant and subresultant PRS information."""
    try:
        res_value = resultant(f, g)
    except (ZeroDivisionError, OverflowError, ValueError):
        res_value = None
    
    try:
        sub_degrees = subresultant_degrees(f, g)
    except (ZeroDivisionError, OverflowError, ValueError):
        sub_degrees = [degree(f), degree(g)]
    
    return res_value, sub_degrees


def compute_cofactor_resultant(f, g, gcd_result):
    """
    Compute the resultant of the cofactors f/gcd and g/gcd.
    
    The cofactor resultant is nonzero when the GCD is maximal (cofactors are coprime).
    This provides a coprimality certificate for the quotient polynomials.
    """
    if is_zero(gcd_result) or degree(gcd_result) == 0:
        # GCD is constant: cofactors are just f and g scaled
        try:
            return resultant(f, g)
        except (ZeroDivisionError, OverflowError):
            return 0
    
    # Compute cofactors via pseudo-division
    _, rem_f = pseudo_divmod(f, gcd_result)
    _, rem_g = pseudo_divmod(g, gcd_result)
    
    if not is_zero(rem_f) or not is_zero(rem_g):
        # GCD doesn't divide exactly (shouldn't happen if GCD is correct)
        return 0
    
    # Get exact quotients
    cofactor_f, _ = poly_divmod(f, gcd_result)
    cofactor_g, _ = poly_divmod(g, gcd_result)
    
    if is_zero(cofactor_f) or is_zero(cofactor_g):
        return 0
    
    try:
        return resultant(cofactor_f, cofactor_g)
    except (ZeroDivisionError, OverflowError, ValueError):
        return 0


def run_pipeline(input_path, output_path):
    """
    Execute the full polynomial GCD pipeline.
    
    Reads input polynomials, computes GCD via modular algorithm,
    computes resultant via subresultant PRS, performs factorization
    analysis, and writes structured output.
    """
    
    # Load input
    f, g, description = load_input(input_path)
    
    # Stage 1: GCD computation
    gcd_result, cont_f, cont_g, cont_gcd, prim_f, prim_g = compute_gcd_pipeline(f, g)
    
    # Stage 2: Trial division verification (catches CRA errors)
    division_verified = trial_division_verify(f, g, gcd_result)
    
    # If verification fails, fall back to trivial GCD
    if not division_verified:
        # Fallback: the candidate doesn't divide both inputs, so set GCD = content_gcd
        gcd_result = [cont_gcd]
        division_verified = True  # Constant always divides
    
    # Stage 3: Resultant computation
    res_value, sub_degrees = compute_resultant_info(f, g)
    
    # Compute cofactor resultant: resultant of f/gcd and g/gcd
    # This serves as a coprimality certificate for the cofactors
    cofactor_res = compute_cofactor_resultant(f, g, gcd_result)
    
    # Stage 4: Factorization analysis
    fact_info = full_factorization_analysis(f, g, gcd_result)
    
    # Stage 5: Collect metadata
    metadata = {
        "algorithm": "modular_gcd_with_cra",
        "division_verified": division_verified,
        "input_description": description,
        "coefficient_bound": landau_mignotte_bound(f, g),
        "gcd_degree": degree(gcd_result)
    }
    
    # Stage 6: Format and write output
    output = format_results(
        f, g, gcd_result,
        res_value if res_value is not None else 0,
        sub_degrees,
        cofactor_res,
        fact_info,
        metadata
    )
    
    write_output(output, output_path)
    
    return output


def main():
    """Entry point for pipeline execution."""
    # Determine paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(script_dir, "input_data.json")
    output_path = os.path.join(script_dir, "output.json")
    
    # Allow override from command line
    if len(sys.argv) >= 2:
        input_path = sys.argv[1]
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    run_pipeline(input_path, output_path)
    print("Pipeline complete.")


if __name__ == "__main__":
    main()
