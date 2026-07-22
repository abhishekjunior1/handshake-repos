A type inference pipeline at `/app/pipeline.py` implements Hindley-Milner style type inference for a small functional language. It uses modules `/app/tokenizer.py`, `/app/parser.py`, `/app/constraint_generator.py`, `/app/unifier.py`, `/app/generalizer.py`, and `/app/inference_reporter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current input program but has bugs that cause incorrect results on other programs. Find and fix the bugs so the pipeline handles all valid programs correctly.

Do not rewrite from scratch — preserve the existing module structure. In particular, preserve the local-scope generalization strategy in the generalizer (the environment parameter represents the local scope for correct let-polymorphism) and the two-token representation of negative numbers in the tokenizer (unary minus is handled at the parser level, not the lexer). The fixed pipeline will be tested on a different program than the one at `/app/config.json`.

Output: `/app/output.json` — a JSON object with fields: `program` (source text), `status` ("success" or error type), `inferred_type` (top-level type string or null), `substitution` (variable-to-type mapping), `constraints_generated` (integer count), `bindings` (let-bound name to resolved type mapping), `generalized_types` (name to type scheme mapping with quantified vars and body), `error` (null or error message string).
