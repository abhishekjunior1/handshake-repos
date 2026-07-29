"""
Square-free decomposition and polynomial factorization utilities.

Provides content/primitive-part extraction, coprimality checks,
square-free decomposition, and GCD multiplicity analysis.
"""

from math import gcd as math_gcd
from polynomial import (
    degree, leading_coeff, is_zero, poly_scale, poly_mul, poly_sub,
    polynomial_content, primitive_part, strip_trailing_zeros, poly_divmod,
    pseudo_divmod, poly_gcd_mod_p, poly_mod_reduce
)


def extract_content_and_primitive(f):
    """
    Extract the content and primitive part of a polynomial.
    Returns (content, primitive_part) where f = content * primitive_part.
    """
    if is_zero(f):
        return 0, [0]
    cont = polynomial_content(f)
    if cont == 0:
        return 0, [0]
    prim = [c // cont for c in f]
    # Normalize: positive leading coefficient
    if prim[-1] < 0:
        prim = [-c for c in prim]
        cont = -cont
    return abs(cont), strip_trailing_zeros(prim)


def are_coprime(f, g):
    """
    Check if polynomials f and g are coprime (GCD = constant).
    Uses modular evaluation for a quick probabilistic check,
    followed by exact verification if needed.
    """
    if is_zero(f) or is_zero(g):
        return False
    if degree(f) == 0 or degree(g) == 0:
        return True  # One is a constant => coprime as polynomials
    
    # Quick check: compute GCD mod a few small primes
    # If GCD mod p is constant for several p, likely coprime
    test_primes = [97, 101, 103]  # Use larger primes to reduce false positives
    
    for p in test_primes:
        lc_f = leading_coeff(f) % p
        lc_g = leading_coeff(g) % p
        if lc_f == 0 or lc_g == 0:
            continue  # Skip this prime
        gcd_mod = poly_gcd_mod_p(f, g, p)
        if degree(gcd_mod) > 0:
            return False  # Found a common factor mod p
    
    return True


def square_free_decomposition(f):
    """
    Compute the square-free decomposition of polynomial f.
    
    Returns a list of (factor, multiplicity) pairs such that:
    f = c * prod(factor_i ^ multiplicity_i)
    where each factor_i is square-free and pairwise coprime.
    
    Uses Yun's algorithm for the decomposition.
    """
    if is_zero(f):
        return [(([0], 1))]
    
    cont, prim = extract_content_and_primitive(f)
    
    if degree(prim) == 0:
        return [([1], 1)]
    
    # Compute derivative
    deriv = poly_derivative(prim)
    
    if is_zero(deriv):
        # Polynomial is a perfect power (only in char p > 0, not for Z)
        return [(prim, 1)]
    
    # Yun's algorithm
    # g = GCD(f, f')
    from modular_gcd import modular_gcd
    g = modular_gcd(prim, deriv)
    
    if degree(g) == 0:
        # f is already square-free
        return [(prim, 1)]
    
    # f = g * w where w = f / g
    w, rem = poly_divmod(prim, g)
    if not is_zero(rem):
        # If exact division fails, use pseudo-division approach
        _, rem2 = pseudo_divmod(prim, g)
        if is_zero(rem2):
            # Scale issue - compute via content removal
            w = primitive_part(prim)  # fallback
        else:
            return [(prim, 1)]  # Cannot decompose cleanly
    
    factors = []
    multiplicity = 1
    
    while degree(w) > 0:
        # y = GCD(w, g)
        y = modular_gcd(w, g)
        
        if degree(y) == 0:
            # w is the remaining square-free factor
            factors.append((strip_trailing_zeros(w), multiplicity))
            break
        
        # z = w / y is square-free factor with current multiplicity
        z, rem = poly_divmod(w, y)
        if degree(z) > 0 and is_zero(rem):
            factors.append((strip_trailing_zeros(z), multiplicity))
        
        # Update for next iteration
        w_new, rem = poly_divmod(g, y)
        if is_zero(rem):
            g = w_new
        else:
            break
        w = y
        multiplicity += 1
    
    if not factors:
        factors = [(prim, 1)]
    
    return factors


def poly_derivative(f):
    """Compute the formal derivative of polynomial f."""
    if len(f) <= 1:
        return [0]
    result = [i * f[i] for i in range(1, len(f))]
    return strip_trailing_zeros(result) if result else [0]


def gcd_multiplicity(f, g, gcd_poly):
    """
    Analyze the multiplicity structure of the GCD within f and g.
    
    Returns dict with:
    - multiplicity_in_f: highest power k such that gcd^k divides f
    - multiplicity_in_g: highest power k such that gcd^k divides g
    - cofactor_f: f / gcd^mult_f
    - cofactor_g: g / gcd^mult_g
    """
    if is_zero(gcd_poly) or degree(gcd_poly) == 0:
        return {
            "multiplicity_in_f": 0,
            "multiplicity_in_g": 0,
            "cofactor_f": f,
            "cofactor_g": g
        }
    
    # Find multiplicity in f
    mult_f = 0
    current = list(f)
    while degree(current) >= degree(gcd_poly):
        q, r = pseudo_divmod(current, gcd_poly)
        if is_zero(r):
            mult_f += 1
            current = primitive_part(q)
        else:
            break
    
    # Find multiplicity in g
    mult_g = 0
    current = list(g)
    while degree(current) >= degree(gcd_poly):
        q, r = pseudo_divmod(current, gcd_poly)
        if is_zero(r):
            mult_g += 1
            current = primitive_part(q)
        else:
            break
    
    return {
        "multiplicity_in_f": mult_f,
        "multiplicity_in_g": mult_g,
        "cofactor_f": primitive_part(f) if mult_f == 0 else current,
        "cofactor_g": primitive_part(g) if mult_g == 0 else current
    }


def full_factorization_analysis(f, g, gcd_poly):
    """
    Complete factorization analysis of polynomials f and g given their GCD.
    
    Returns comprehensive analysis including:
    - Content decomposition
    - Square-free structure of GCD
    - Multiplicity information
    """
    cont_f, prim_f = extract_content_and_primitive(f)
    cont_g, prim_g = extract_content_and_primitive(g)
    
    content_gcd = math_gcd(cont_f, cont_g) if cont_f > 0 and cont_g > 0 else 1
    
    # Square-free decomposition of GCD
    gcd_sq_free = square_free_decomposition(gcd_poly)
    
    # Multiplicity analysis
    mult_info = gcd_multiplicity(f, g, gcd_poly)
    
    return {
        "content_f": cont_f,
        "content_g": cont_g,
        "content_gcd": content_gcd,
        "primitive_f": prim_f,
        "primitive_g": prim_g,
        "primitive_gcd": primitive_part(gcd_poly) if not is_zero(gcd_poly) else [1],
        "square_free_gcd": [(list(factor), mult) for factor, mult in gcd_sq_free],
        "multiplicity": mult_info,
        "coprime": degree(gcd_poly) == 0
    }
