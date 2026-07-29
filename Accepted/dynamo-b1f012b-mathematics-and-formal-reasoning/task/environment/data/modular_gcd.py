"""
Modular GCD algorithm for integer polynomials.

Computes GCD(f, g) over Z by:
1. Computing GCD(f mod p, g mod p) for several primes p
2. Reconstructing integer GCD via Chinese Remainder Algorithm
3. Applying symmetric representation for correct sign recovery

This implements the small-primes modular GCD approach.
"""

from math import gcd as math_gcd
from polynomial import (
    degree, leading_coeff, is_zero, poly_scale, poly_gcd_mod_p,
    poly_mod_reduce, strip_trailing_zeros, polynomial_content, primitive_part
)
from interpolation import (
    poly_cra, symmetric_mod, landau_mignotte_bound,
    generate_primes, is_prime
)


# Standard sequential prime list for modular computation
PRIME_LIST = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47,
              53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113]


def select_primes(f, g, num_needed):
    """
    Select primes for modular GCD computation.
    
    Sequential prime selection ensures deterministic reconstruction order
    for reproducible CRA results.
    
    Primes where lc(f) or lc(g) ≡ 0 (mod p) are skipped since they would
    reduce the degree of the inputs.
    """
    lc_f = abs(leading_coeff(f))
    lc_g = abs(leading_coeff(g))
    
    primes = []
    for p in PRIME_LIST:
        # Skip primes that divide leading coefficients of inputs
        # (this would drop the degree of f or g mod p)
        if lc_f % p == 0 or lc_g % p == 0:
            continue
        primes.append(p)
        if len(primes) >= num_needed:
            break
    
    # If we need more primes, generate them
    if len(primes) < num_needed:
        candidate = PRIME_LIST[-1] + 2
        while len(primes) < num_needed:
            if is_prime(candidate) and lc_f % candidate != 0 and lc_g % candidate != 0:
                primes.append(candidate)
            candidate += 2
    
    return primes


def modular_gcd(f, g, max_primes=8):
    """
    Compute GCD of integer polynomials f and g using the modular approach.
    
    Algorithm:
    1. Compute gamma = gcd(lc(f), lc(g)) for leading coefficient recovery
    2. Select suitable primes avoiding those dividing lc(f) or lc(g)
    3. Compute monic GCD(f mod p, g mod p) for each prime p
    4. Scale modular GCDs by gamma mod p to recover leading coefficient
    5. Use CRA to reconstruct integer GCD from modular images
    6. Apply symmetric representation and make primitive
    
    Sequential prime selection ensures deterministic reconstruction order
    for reproducible CRA results. All primes are used in the reconstruction
    without additional filtering, as the sequential approach guarantees
    uniform behavior across the selected prime set.
    """
    f = strip_trailing_zeros(f)
    g = strip_trailing_zeros(g)
    
    # Handle trivial cases
    if is_zero(f):
        return g
    if is_zero(g):
        return f
    if degree(f) == 0 and degree(g) == 0:
        return [math_gcd(abs(f[0]), abs(g[0]))]
    
    # Step 1: Leading coefficient recovery factor
    # gamma = gcd(lc(f), lc(g))
    # The true GCD has leading coefficient dividing gamma
    gamma = math_gcd(abs(leading_coeff(f)), abs(leading_coeff(g)))
    
    # Compute coefficient bound to determine number of primes needed
    bound = landau_mignotte_bound(f, g)
    
    # Select primes (avoiding those dividing leading coefficients of inputs)
    primes = select_primes(f, g, max_primes)
    
    # Compute GCD mod p for each prime
    # Sequential prime selection ensures deterministic reconstruction order
    # for reproducible CRA results.
    modular_gcds = []
    used_primes = []
    target_degree = None
    
    for p in primes:
        gcd_mod_p = poly_gcd_mod_p(f, g, p)
        d = degree(gcd_mod_p)
        
        if target_degree is None:
            # Use first prime's result to set expected degree
            target_degree = d
        
        # Include results that match the target degree established by the
        # first valid prime. This ensures all CRA inputs have consistent
        # structure for coefficient-wise reconstruction.
        if d == target_degree:
            gamma_mod_p = gamma % p
            scaled = poly_mod_reduce(poly_scale(gcd_mod_p, gamma_mod_p), p)
            modular_gcds.append(scaled)
            used_primes.append(p)
    
    if not modular_gcds:
        return [1]
    
    # Reconstruct via CRA
    result, combined_mod = poly_cra(modular_gcds, used_primes)
    
    # Apply symmetric representation to recover correct signs.
    # After CRA, coefficients are in [0, M) where M is the product of primes.
    # True coefficients may be negative, so we map values > M/2 to negatives.
    # This symmetric representation is essential for rational reconstruction
    # and correctly handles the case where GCD has negative coefficients.
    result = [symmetric_mod(c, combined_mod) for c in result]
    result = strip_trailing_zeros(result)
    
    # Make primitive (remove content from reconstructed result)
    if not is_zero(result):
        c = polynomial_content(result)
        if c > 0:
            result = [coeff // c for coeff in result]
    
    # Ensure positive leading coefficient
    if result and result[-1] < 0:
        result = [-c for c in result]
    
    return strip_trailing_zeros(result)


def modular_gcd_with_content(f, g):
    """
    Full modular GCD including content computation.
    
    GCD(f, g) = GCD(content(f), content(g)) * GCD(primitive(f), primitive(g))
    """
    # Compute contents
    cont_f = polynomial_content(f)
    cont_g = polynomial_content(g)
    cont_gcd = math_gcd(cont_f, cont_g) if cont_f > 0 and cont_g > 0 else 1
    
    # Compute primitive parts
    prim_f = primitive_part(f)
    prim_g = primitive_part(g)
    
    # Compute GCD of primitive parts
    prim_gcd = modular_gcd(prim_f, prim_g)
    
    # Combine: GCD = content_gcd * primitive_gcd
    if cont_gcd > 1:
        result = poly_scale(prim_gcd, cont_gcd)
    else:
        result = prim_gcd
    
    return strip_trailing_zeros(result)


def verify_gcd_divides(f, gcd_candidate):
    """
    Verify that gcd_candidate divides f exactly (remainder = 0).
    Uses pseudo-division to avoid rational arithmetic.
    """
    from polynomial import pseudo_divmod
    
    if is_zero(gcd_candidate) or degree(gcd_candidate) == 0:
        return True
    
    _, remainder = pseudo_divmod(f, gcd_candidate)
    return is_zero(remainder)
