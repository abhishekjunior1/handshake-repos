"""
Solution for the polynomial GCD computation pipeline.

Fixes three bugs across three modules:

1. modular_gcd.py: Uses first prime's GCD degree as target, keeping only
   matching results. If the first prime is unlucky (spurious common factor),
   correct lower-degree results get discarded. Fix: collect all results,
   find minimum degree (true GCD degree), discard higher-degree results.

2. pipeline.py: Scales the primitive GCD by content_f instead of
   content_gcd = gcd(content_f, content_g). This over-scales when
   content_f > content_gcd. Fix: use content_gcd for scaling.

3. resultant.py: The delta (defect) calculation uses deg_prev - deg_curr + 1
   instead of deg_prev - deg_curr. The extra +1 corrupts the psi scaling
   coefficient in the subresultant PRS. Fix: remove the +1.
"""

import subprocess
import sys


def patch_file(filepath, old, new, label=""):
    """Apply a string replacement patch to a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    if old not in content:
        print(f"  {label}: FAILED - target not found", file=sys.stderr)
        return False
    content = content.replace(old, new)
    with open(filepath, 'w') as f:
        f.write(content)
    print(f"  {label}: OK")
    return True


def main():
    print("Applying patches...")

    # Fix 1: modular_gcd.py - filter unlucky primes by minimum degree
    patch_file(
        "/app/modular_gcd.py",
        """    # Compute GCD mod p for each prime
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
            used_primes.append(p)""",
        """    # Compute GCD mod p for each prime, filtering unlucky primes
    modular_gcds = []
    used_primes = []
    all_results = []
    
    for p in primes:
        gcd_mod_p = poly_gcd_mod_p(f, g, p)
        d = degree(gcd_mod_p)
        all_results.append((p, gcd_mod_p, d))
    
    # The true GCD degree is the minimum observed across all primes
    min_degree = min(d for _, _, d in all_results)
    
    # Keep only results matching the minimum degree (discard unlucky primes)
    for p, gcd_mod_p, d in all_results:
        if d == min_degree:
            gamma_mod_p = gamma % p
            scaled = poly_mod_reduce(poly_scale(gcd_mod_p, gamma_mod_p), p)
            modular_gcds.append(scaled)
            used_primes.append(p)""",
        "modular_gcd.py"
    )

    # Fix 2: pipeline.py - use content_gcd instead of content_f
    patch_file(
        "/app/pipeline.py",
        """    # Scale by the input content factor for full-coefficient GCD representation.
    # The content of f provides the natural scaling for the output GCD since
    # the GCD divides f and inherits its coefficient magnitude.
    if content_f > 1:
        gcd_result = [c * content_f for c in primitive_gcd]""",
        """    # Scale by content GCD for correct full-coefficient representation.
    if content_gcd > 1:
        gcd_result = [c * content_gcd for c in primitive_gcd]""",
        "pipeline.py"
    )

    # Fix 3: resultant.py - correct delta calculation
    patch_file(
        "/app/resultant.py",
        """        # Degree difference gives the exact step size for the pseudo-remainder scaling.
        delta = deg_prev - deg_curr + 1""",
        """        # Degree difference gives the exact step size for the pseudo-remainder scaling.
        delta = deg_prev - deg_curr""",
        "resultant.py"
    )

    # Run the pipeline
    print("Running pipeline...")
    subprocess.run(["python3", "/app/pipeline.py"], check=True)
    print("Done.")


if __name__ == "__main__":
    main()
