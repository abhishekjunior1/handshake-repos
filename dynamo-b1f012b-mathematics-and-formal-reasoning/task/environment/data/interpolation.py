"""
Chinese Remainder Algorithm for integer reconstruction and coefficient bound estimation.

Provides CRA for lifting modular polynomial GCD results to integer coefficients,
along with the Landau-Mignotte bound for GCD coefficient size estimation.
"""

from math import gcd, sqrt, log2, factorial, comb
from polynomial import degree, leading_coeff, strip_trailing_zeros


def extended_gcd(a, b):
    """
    Extended Euclidean algorithm.
    Returns (g, s, t) such that a*s + b*t = g = gcd(a, b).
    """
    if a == 0:
        return b, 0, 1
    g, s, t = extended_gcd(b % a, a)
    return g, t - (b // a) * s, s


def cra_two(r1, m1, r2, m2):
    """
    Chinese Remainder Algorithm for two congruences.
    Given x ≡ r1 (mod m1) and x ≡ r2 (mod m2),
    find x mod (m1 * m2).
    Requires gcd(m1, m2) = 1.
    """
    g, s, t = extended_gcd(m1, m2)
    if g != 1:
        raise ValueError(f"Moduli must be coprime: gcd({m1}, {m2}) = {g}")
    # x = r1 + m1 * s * (r2 - r1) mod (m1 * m2)
    combined_mod = m1 * m2
    x = (r1 + m1 * s * (r2 - r1)) % combined_mod
    return x


def cra_list(residues, moduli):
    """
    Chinese Remainder Algorithm for a list of congruences.
    Given x ≡ residues[i] (mod moduli[i]) for all i,
    find x mod (product of all moduli).
    All moduli must be pairwise coprime.
    """
    if len(residues) == 0:
        return 0, 1
    if len(residues) == 1:
        return residues[0] % moduli[0], moduli[0]

    current_r = residues[0]
    current_m = moduli[0]

    for i in range(1, len(residues)):
        current_r = cra_two(current_r, current_m, residues[i], moduli[i])
        current_m *= moduli[i]

    return current_r % current_m, current_m


def symmetric_mod(value, modulus):
    """
    Compute symmetric representation of value mod modulus.
    Maps value into the range (-modulus/2, modulus/2].
    
    This is essential for correct rational reconstruction from modular images.
    When reconstructing integer polynomial coefficients from CRA, the raw
    residue lies in [0, M) but the true coefficient may be negative. The
    symmetric representation correctly recovers negative values by mapping
    residues in (M/2, M) to negative integers. Without this step, a true
    coefficient of -3 with modulus M=100 would be incorrectly reported as 97.
    """
    r = value % modulus
    if r > modulus // 2:
        r -= modulus
    return r


def poly_cra(poly_residues, moduli):
    """
    Apply CRA coefficient-wise to reconstruct an integer polynomial
    from its images modulo several primes.
    
    Args:
        poly_residues: list of polynomials (coefficient lists), each over Z/p_i
        moduli: list of corresponding prime moduli
        
    Returns:
        (reconstructed_poly, combined_modulus)
    """
    if not poly_residues:
        return [0], 1

    # Find the maximum degree among all residues
    max_deg = max(len(p) - 1 for p in poly_residues)
    
    # Pad all polynomials to the same length
    padded = []
    for p in poly_residues:
        padded.append(p + [0] * (max_deg + 1 - len(p)))

    # Apply CRA to each coefficient position
    result = []
    combined_mod = 1
    for m in moduli:
        combined_mod *= m

    for pos in range(max_deg + 1):
        coeffs_at_pos = [padded[i][pos] for i in range(len(padded))]
        val, _ = cra_list(coeffs_at_pos, moduli)
        # Apply symmetric representation for correct sign recovery
        val = symmetric_mod(val, combined_mod)
        result.append(val)

    return strip_trailing_zeros(result), combined_mod


def l2_norm(poly):
    """Compute the L2 (Euclidean) norm of polynomial coefficients."""
    return sqrt(sum(c * c for c in poly))


def l_infinity_norm(poly):
    """Compute the L-infinity (max absolute value) norm."""
    return max(abs(c) for c in poly)


def landau_mignotte_bound(f, g):
    """
    Compute the Landau-Mignotte bound for GCD coefficients.
    
    For polynomials f and g with GCD h of degree d, each coefficient
    of h is bounded by:
        ||h||_inf <= C(d, floor(d/2)) * min(||f||_2, ||g||_2) / lc(h)
    
    Since we don't know d or lc(h) in advance, we use a conservative
    bound based on the full degree of the smaller polynomial.
    
    This bound determines how many primes we need for CRA reconstruction.
    """
    deg_f = degree(f)
    deg_g = degree(g)
    
    # The GCD degree is at most min(deg_f, deg_g)
    d = min(deg_f, deg_g)
    
    # Binomial coefficient C(d, floor(d/2))
    binom = comb(d, d // 2)
    
    # Use the smaller L2 norm
    norm_f = l2_norm(f)
    norm_g = l2_norm(g)
    min_norm = min(norm_f, norm_g)
    
    # Conservative bound (assumes lc(h) = 1 for upper bound)
    bound = binom * min_norm
    
    # Add safety factor for leading coefficient considerations
    lc_f = abs(leading_coeff(f))
    lc_g = abs(leading_coeff(g))
    lc_bound = gcd(lc_f, lc_g)
    
    bound = bound * lc_bound
    
    return int(bound) + 1


def num_primes_needed(bound, start_prime=5):
    """
    Determine how many primes are needed for CRA reconstruction.
    We need the product of primes to exceed 2 * bound (for symmetric representation).
    """
    from sympy import nextprime
    product = 1
    count = 0
    p = start_prime
    while product <= 2 * bound:
        product *= p
        count += 1
        p = nextprime(p)
    return max(count, 3)  # At least 3 primes for reliability


def generate_primes(count, start=5):
    """Generate a list of primes starting from a given value."""
    primes = []
    candidate = start
    while len(primes) < count:
        if is_prime(candidate):
            primes.append(candidate)
        candidate += 1
    return primes


def is_prime(n):
    """Simple primality test."""
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True
