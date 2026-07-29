A feature flag evaluation pipeline at `/app/pipeline.py` evaluates feature flags for a device fleet, determining which flags are enabled or disabled for each device based on targeting rules, rollout percentages, dependency constraints, and mutual exclusion groups. It uses modules `/app/flag_loader.py`, `/app/targeting_engine.py`, `/app/rollout_calculator.py`, `/app/dependency_resolver.py`, `/app/conflict_resolver.py`, and `/app/output_formatter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The pipeline produces correct evaluation results on the current input but has bugs that cause incorrect results on other configurations. Find and fix the bugs so the pipeline handles all valid inputs correctly.

Do not rewrite from scratch — preserve the existing module structure and evaluation conventions. Preserve the alphabetical flag-name sorting before evaluation (required for deterministic mutual exclusion resolution via last-writer-wins semantics) and the full-fleet evaluation including stale devices (staleness filtering is a downstream presentation concern, not an evaluation concern).

The fixed pipeline will be tested on a different configuration than the one at `/app/config.json`. The test configuration will include flags with partial rollout percentages, dependency chains between flags, and multiple mutual exclusion groups.

In this system, dependency constraints (`requires`) gate on targeting eligibility — a flag's prerequisite must pass targeting to satisfy the dependency, regardless of whether the prerequisite is later excluded by rollout bucketing. This is because rollout is a gradual-release mechanism (the prerequisite will eventually reach 100%), while dependencies express capability requirements (the prerequisite's feature must exist in the codebase for the dependent to function). A dependent flag may be enabled for a device even if its prerequisite is currently outside the rollout cohort for that device.

Output: `/app/output.json` — a JSON object with three top-level keys: `evaluations` (nested object mapping device_id to flag_name to `{"enabled": bool, "reason": string}`), `summary` (object with `total_devices`, `total_flags`, `total_evaluations`, `enabled_count`, `disabled_count`, `dependency_overrides`, `conflict_resolutions`), and `metadata` (object with `flags_evaluated` array, `devices_evaluated` integer, `mutex_groups_processed` integer, `dependency_chains_resolved` integer, `rollout_hash_method` string).
