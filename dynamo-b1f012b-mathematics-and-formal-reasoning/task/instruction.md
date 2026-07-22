A polynomial computation pipeline at `/app/pipeline.py` computes GCD, resultant, and factorization properties of univariate polynomials over the integers using modular methods. It uses modules `/app/polynomial.py`, `/app/modular_gcd.py`, `/app/resultant.py`, `/app/factorization.py`, `/app/interpolation.py`, and `/app/output_formatter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/input_data.json` and writes `/app/output.json`.

The pipeline produces correct output on the current input but has bugs that cause incorrect results on other inputs. Find and fix the bugs so the pipeline handles all valid inputs correctly.

Do not rewrite from scratch — preserve the existing module structure and computational conventions. In particular, preserve the symmetric coefficient reduction after CRA reconstruction (which ensures correct rational reconstruction from modular images) and the trial division verification step (which validates the GCD candidate against both inputs before reporting).

The fixed pipeline will be tested on a different input than the one at `/app/input_data.json`. The test input will use polynomials with non-unit content, non-trivial GCD, and coefficients that exercise all computation paths including the cofactor resultant (resultant of f/gcd and g/gcd).

Output: `/app/output.json` — JSON with fields `input_polynomials`, `gcd` (with `coefficients`, `degree`, `leading_coefficient`, `verified`), `resultant` (with `value`, `subresultant_degrees`, `cofactor_resultant`), `factorization` (with `content_f`, `content_g`, `content_gcd`, `primitive_gcd`, `square_free_gcd`, `coprime`), and `computation_metadata` (with `algorithm`, `gcd_degree`).
