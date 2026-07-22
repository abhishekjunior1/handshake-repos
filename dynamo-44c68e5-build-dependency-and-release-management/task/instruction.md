A Nix-style derivation hash pipeline at `/app/pipeline.py` computes content-addressed store paths for build derivations, validates binary cache entries, and produces a build plan. It uses modules `/app/derivation_parser.py`, `/app/hash_computer.py`, `/app/dependency_resolver.py`, `/app/store_path_calculator.py`, `/app/cache_validator.py`, `/app/build_scheduler.py`, and `/app/output_formatter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/build_config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current build configuration but has bugs that cause incorrect store paths, cache validation failures, and wrong build plans on configurations with fixed-output derivations, compressed cache entries, and self-referencing outputs. Find and fix the bugs so the pipeline handles all valid derivation configurations correctly.

Do not rewrite from scratch — preserve the existing module structure and conventions. Preserve the Nix base32 encoding with reversed character order used in store path computation. Preserve the input derivation output selection using the "!" separator notation for multi-output derivation references. The fixed pipeline will be tested on a different build configuration than the one at `/app/build_config.json`.

Output: `/app/output.json` — a JSON object with `store_paths` (object mapping derivation name to computed store path string), `build_plan` (object with `to_build` list of build action objects, `to_substitute` list of substitute action objects, `total_builds` integer, `total_substitutes` integer), and `system` (object with `platform`, `arch`, `os` strings).
