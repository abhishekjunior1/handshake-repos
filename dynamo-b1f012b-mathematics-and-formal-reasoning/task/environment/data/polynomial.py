"""
Basic polynomial arithmetic over integers and Z/pZ.

Polynomials are represented as lists of coefficients [a0, a1, a2, ...]
where the index corresponds to the degree of that term.
E.g., [3, 2, 1] represents 3 + 2x + x^2.
"""

from math import gcd as math_gcd
from functools import reduce


def strip_trailing_zeros(poly):
    """Remove trailing zero coefficients to normalize representation."""
    while len(poly) > 1 and poly[-1] == 0:
        poly = poly[:-1]
    return poly


def degree(poly):
    """Return the degree of the polynomial. deg(0) = -1 by convention."""
    p = strip_trailing_zeros(poly)
    if p == [0]:
        return -1
    return len(p) - 1


def leading_coeff(poly):
    """Return the leading (highest-degree) coefficient."""
    p = strip_trailing_zeros(poly)
    return p[-1]


def is_zero(poly):
    """Check if polynomial is the zero polynomial."""
    return strip_trailing_zeros(poly) == [0]


def poly_add(f, g):
    """Add two polynomials over Z."""
    n = max(len(f), len(g))
    result = [0] * n
    for i in range(len(f)):
        result[i] += f[i]
    for i in range(len(g)):
        result[i] += g[i]
    return strip_trailing_zeros(result)


def poly_sub(f, g):
    """Subtract polynomial g from f over Z."""
    n = max(len(f), len(g))
    result = [0] * n
    for i in range(len(f)):
        result[i] += f[i]
    for i in range(len(g)):
        result[i] -= g[i]
    return strip_trailing_zeros(result)


def poly_mul(f, g):
    """Multiply two polynomials over Z."""
    if is_zero(f) or is_zero(g):
        return [0]
    n = len(f) + len(g) - 1
    result = [0] * n
    for i in range(len(f)):
        for j in range(len(g)):
            result[i + j] += f[i] * g[j]
    return strip_trailing_zeros(result)


def poly_scale(f, c):
    """Multiply polynomial f by scalar c."""
    if c == 0:
        return [0]
    return strip_trailing_zeros([coeff * c for coeff in f])


def poly_divmod(f, g):
    """
    Polynomial division with remainder over Q (exact integer division).
    Returns (quotient, remainder) such that f = q*g + r and deg(r) < deg(g).
    Requires that all divisions are exact (integer coefficients).
    """
    f = list(strip_trailing_zeros(f))
    g = strip_trailing_zeros(g)
    if is_zero(g):
        raise ValueError("Division by zero polynomial")
    if degree(f) < degree(g):
        return [0], f

    dg = degree(g)
    lg = leading_coeff(g)
    quotient = [0] * (degree(f) - dg + 1)

    while degree(f) >= dg and not is_zero(f):
        df = degree(f)
        lf = leading_coeff(f)
        if lf % lg != 0:
            # Cannot do exact division; use pseudo-division scaling
            break
        coeff = lf // lg
        quotient[df - dg] = coeff
        for i in range(len(g)):
            f[i + df - dg] -= coeff * g[i]
        f = strip_trailing_zeros(f)

    return strip_trailing_zeros(quotient), strip_trailing_zeros(f)


def pseudo_divmod(f, g):
    """
    Pseudo-division: compute q, r such that lc(g)^(deg(f)-deg(g)+1) * f = q*g + r.
    This avoids fractions entirely.
    """
    f = list(strip_trailing_zeros(f))
    g = strip_trailing_zeros(g)
    if is_zero(g):
        raise ValueError("Division by zero polynomial")
    if degree(f) < degree(g):
        return [0], f

    dg = degree(g)
    lg = leading_coeff(g)
    delta = degree(f) - dg + 1
    quotient = [0] * (degree(f) - dg + 1)

    while degree(f) >= dg and not is_zero(f) and delta > 0:
        df = degree(f)
        lf = leading_coeff(f)
        # Scale f by lc(g) and subtract
        quotient = [c * lg for c in quotient]
        quotient[df - dg] += lf
        f = [c * lg for c in f]
        for i in range(len(g)):
            f[i + df - dg] -= lf * g[i]
        f = strip_trailing_zeros(f)
        delta -= 1

    # Scale quotient and remainder by remaining power of lg
    scale = lg ** delta
    quotient = [c * scale for c in quotient]
    f = [c * scale for c in f]

    return strip_trailing_zeros(quotient), strip_trailing_zeros(f)


def polynomial_content(f):
    """Compute the content of f: GCD of all coefficients."""
    f = strip_trailing_zeros(f)
    if is_zero(f):
        return 0
    coeffs = [abs(c) for c in f if c != 0]
    if not coeffs:
        return 0
    result = coeffs[0]
    for c in coeffs[1:]:
        result = math_gcd(result, c)
    # Make content positive by convention
    return result


def primitive_part(f):
    """Divide polynomial by its content to get the primitive part."""
    c = polynomial_content(f)
    if c == 0:
        return [0]
    result = [coeff // c for coeff in f]
    # Ensure leading coefficient is positive
    if result[-1] < 0:
        result = [-x for x in result]
    return strip_trailing_zeros(result)


def evaluate(f, x):
    """Evaluate polynomial f at point x using Horner's method."""
    f = strip_trailing_zeros(f)
    result = 0
    for i in range(len(f) - 1, -1, -1):
        result = result * x + f[i]
    return result


# --- Modular arithmetic (Z/pZ) ---

def poly_mod_reduce(f, p):
    """Reduce polynomial coefficients mod p."""
    result = [c % p for c in f]
    return strip_trailing_zeros(result)


def poly_mod_add(f, g, p):
    """Add polynomials mod p."""
    result = poly_add(f, g)
    return poly_mod_reduce(result, p)


def poly_mod_sub(f, g, p):
    """Subtract polynomials mod p."""
    result = poly_sub(f, g)
    return poly_mod_reduce(result, p)


def poly_mod_mul(f, g, p):
    """Multiply polynomials mod p."""
    result = poly_mul(f, g)
    return poly_mod_reduce(result, p)


def mod_inverse(a, p):
    """Compute modular inverse of a mod p using extended Euclidean algorithm."""
    a = a % p
    if a == 0:
        raise ValueError(f"No inverse for 0 mod {p}")
    g, x, _ = extended_gcd(a, p)
    if g != 1:
        raise ValueError(f"No inverse: gcd({a}, {p}) = {g}")
    return x % p


def extended_gcd(a, b):
    """Extended GCD: returns (gcd, x, y) such that a*x + b*y = gcd."""
    if a == 0:
        return b, 0, 1
    g, x, y = extended_gcd(b % a, a)
    return g, y - (b // a) * x, x


def poly_mod_divmod(f, g, p):
    """Polynomial division with remainder over Z/pZ."""
    f = list(poly_mod_reduce(f, p))
    g = poly_mod_reduce(g, p)
    if is_zero(g):
        raise ValueError("Division by zero polynomial mod p")
    if degree(f) < degree(g):
        return [0], poly_mod_reduce(f, p)

    dg = degree(g)
    lg_inv = mod_inverse(leading_coeff(g), p)
    quotient = [0] * (degree(f) - dg + 1)

    while degree(f) >= dg and not is_zero(f):
        df = degree(f)
        lf = f[df]
        coeff = (lf * lg_inv) % p
        quotient[df - dg] = coeff
        for i in range(len(g)):
            idx = i + df - dg
            if idx < len(f):
                f[idx] = (f[idx] - coeff * g[i]) % p
        f = strip_trailing_zeros(f)

    return strip_trailing_zeros(quotient), poly_mod_reduce(f, p)


def poly_gcd_mod_p(f, g, p):
    """
    Compute GCD of f and g over Z/pZ using Euclidean algorithm.
    Returns a monic polynomial (leading coefficient = 1).
    """
    f = poly_mod_reduce(f, p)
    g = poly_mod_reduce(g, p)

    while not is_zero(g):
        _, r = poly_mod_divmod(f, g, p)
        f = g
        g = r

    # Make monic
    if not is_zero(f):
        lc = leading_coeff(f)
        lc_inv = mod_inverse(lc, p)
        f = poly_mod_reduce(poly_scale(f, lc_inv), p)

    return f
