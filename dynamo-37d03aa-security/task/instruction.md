A CIS compliance scanner pipeline at `/app/pipeline.py` evaluates system configurations against a hierarchical benchmark of security controls. It uses modules `/app/config_loader.py`, `/app/rule_parser.py`, `/app/inheritance_engine.py`, `/app/policy_resolver.py`, `/app/exception_handler.py`, `/app/scorer.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The pipeline produces correct compliance results on the current configuration but has bugs that cause incorrect evaluation on other configurations. Find and fix the bugs so the pipeline handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure and the section density normalization that scales scores by relative control count across sections.

The fixed pipeline will be tested on a different configuration than the one at `/app/config.json`.

Output: `/app/output.json` — a JSON object with these sections:

- `summary`: `overall_compliance_score` (float, CVSS-weighted with density normalization), `compliance_status` (PASS/FAIL based on fail_threshold), `total_controls_evaluated` (int), `scored_controls` (int), `informational_controls` (int), `controls_passed` (int), `controls_failed` (int), `controls_waived` (int), `pass_rate` (float, (passed+waived)/scored)
- `section_breakdown`: list of objects with `section_id`, `compliance_score` (float, density-normalized), `total_controls`, `passed`, `failed`, `waived`
- `control_details`: list of objects with `control_id`, `resource_id`, `status` (pass/fail/waived), `severity`, `cvss_score`, `control_type`, `full_path`, `evidence`; waived entries also have `waiver_id`, `waiver_reason`, `original_status`
- `waiver_summary`: `total_waivers_applied` (int), `waivers_by_severity` (dict), `waivers_by_type` (dict), `unique_waivers_used` (int)
- `metadata`: `evaluation_profile`, `scoring_method`, `fail_threshold`, `inheritance_mode`, `exception_match_mode`
