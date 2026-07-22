"""
Subresultant Polynomial Remainder Sequence (PRS) and resultant computation.

The subresultant PRS avoids coefficient explosion in the Euclidean algorithm
by computing controlled pseudo-remainders with exact division.
"""

from polynomial import (
    degree, leading_coeff, is_zero, poly_scale, poly_sub, poly_mul,
    pseudo_divmod, strip_trailing_zeros
)


def subresultant_prs(f, g):
    """
    Compute the subresultant Polynomial Remainder Sequence of f and g.
    
    The subresultant PRS produces a sequence r_0, r_1, r_2, ... where:
    - r_0 = f, r_1 = g
    - Each subsequent r_i is a scaled pseudo-remainder
    - Coefficients remain integers (no fractions) and growth is controlled
    
    Returns list of (polynomial, degree) pairs forming the PRS.
    """
    if is_zero(f):
        return [(g, degree(g))]
    if is_zero(g):
        return [(f, degree(f))]
    
    # Ensure deg(f) >= deg(g)
    if degree(f) < degree(g):
        f, g = g, f
    
    prs = [(list(f), degree(f)), (list(g), degree(g))]
    
    # Initialize scaling coefficients
    # h = leading coefficient of the first remainder
    # psi = 1 initially
    psi = 1
    beta = 1
    
    i = 0
    r_prev = list(f)
    r_curr = list(g)
    
    while not is_zero(r_curr):
        deg_prev = degree(r_prev)
        deg_curr = degree(r_curr)
        
        # Degree difference gives the exact step size for the pseudo-remainder scaling.
        delta = deg_prev - deg_curr + 1
        
        # Compute pseudo-remainder
        lc_curr = leading_coeff(r_curr)
        
        # Scale factor for pseudo-division
        scale = lc_curr ** (delta + 1) if delta >= 0 else 1
        
        # Perform pseudo-division
        _, remainder = pseudo_divmod(r_prev, r_curr)
        
        if is_zero(remainder):
            break
        
        # Compute scaling coefficient beta for exact division
        if i == 0:
            # First iteration: beta = (-1)^(delta+1)
            beta_sign = (-1) ** (delta + 1)
            r_next = [c * beta_sign // 1 for c in remainder]
            # Update psi for next iteration
            psi = (-leading_coeff(r_curr)) ** delta if delta > 0 else 1
        else:
            # Subsequent iterations: divide by psi^delta * lc(r_prev)
            divisor = (psi ** delta) * leading_coeff(r_prev) if delta > 0 else leading_coeff(r_prev)
            if divisor == 0:
                break
            # Exact division of remainder by divisor (with sign)
            sign = (-1) ** (delta + 1)
            r_next = [sign * c // abs(divisor) for c in remainder]
            # Update psi: psi = (-lc(r_curr))^delta / psi^(delta-1)
            if delta > 0 and psi != 0:
                lc_val = (-leading_coeff(r_curr))
                psi = (lc_val ** delta) // (psi ** (delta - 1)) if delta > 1 else lc_val
        
        r_next = strip_trailing_zeros(r_next)
        
        if not is_zero(r_next):
            prs.append((r_next, degree(r_next)))
        
        r_prev = r_curr
        r_curr = r_next
        i += 1
    
    # The last non-zero entry (before zero remainder) is proportional to GCD
    return prs


def resultant(f, g):
    """
    Compute the resultant of polynomials f and g.
    
    The resultant is zero if and only if f and g share a common factor.
    Computed via the subresultant PRS as the last element when GCD is constant.
    
    For polynomials f of degree m and g of degree n:
    res(f, g) = (-1)^(mn) * res(g, f)
    """
    if is_zero(f) or is_zero(g):
        return 0
    
    deg_f = degree(f)
    deg_g = degree(g)
    
    if deg_f == 0 and deg_g == 0:
        return 1  # Both constants, coprime (nonzero)
    
    if deg_f == 0:
        return f[0] ** deg_g
    if deg_g == 0:
        return g[0] ** deg_f
    
    # Compute via subresultant PRS
    prs = subresultant_prs(f, g)
    
    if len(prs) < 2:
        return 0
    
    # The resultant is derived from the last non-trivial entry in the PRS
    last_entry = prs[-1][0]
    last_deg = prs[-1][1]
    
    if last_deg > 0:
        # GCD has positive degree => resultant is 0
        return 0
    elif last_deg == 0:
        # GCD is constant => resultant is the constant raised to appropriate power
        return last_entry[0]
    
    return 0


def resultant_direct(f, g):
    """
    Compute resultant using direct pseudo-remainder sequence (fallback method).
    Simpler but may have larger intermediate coefficients.
    """
    if is_zero(f) or is_zero(g):
        return 0
    
    deg_f = degree(f)
    deg_g = degree(g)
    
    if deg_f == 0:
        return f[0] ** deg_g
    if deg_g == 0:
        return g[0] ** deg_f
    
    # Use simple Euclidean-like approach with tracking of scalar factors
    sign = 1
    a = list(f)
    b = list(g)
    result_factor = 1
    
    while degree(b) > 0:
        da = degree(a)
        db = degree(b)
        
        # Sign adjustment
        if da % 2 == 1 and db % 2 == 1:
            sign = -sign
        
        # Pseudo-remainder
        lc_b = leading_coeff(b)
        scale_power = da - db + 1
        result_factor *= lc_b ** scale_power
        
        _, r = pseudo_divmod(a, b)
        
        if is_zero(r):
            return 0
        
        a = b
        b = r
    
    if is_zero(b):
        return 0
    
    # Final contribution
    db = degree(a)
    res = sign * (leading_coeff(b) ** db) // result_factor if result_factor != 0 else 0
    
    return res


def subresultant_degrees(f, g):
    """
    Return the list of degrees in the subresultant PRS.
    Useful for analyzing the structure of the GCD computation.
    """
    prs = subresultant_prs(f, g)
    return [deg for _, deg in prs]


def prs_gcd(f, g):
    """
    Extract GCD from the subresultant PRS.
    The last non-zero polynomial in the PRS (before zero remainder) is the GCD
    up to a scalar multiple.
    """
    prs = subresultant_prs(f, g)
    if not prs:
        return [1]
    
    # Last entry in PRS is the GCD (up to scalar)
    gcd_poly = prs[-1][0]
    
    if is_zero(gcd_poly):
        # If last entry is zero, take second-to-last
        if len(prs) >= 2:
            gcd_poly = prs[-2][0]
        else:
            return [1]
    
    return strip_trailing_zeros(gcd_poly)
