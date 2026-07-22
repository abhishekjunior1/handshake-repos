A security compliance hardening scanner pipeline at `/app/pipeline.py` evaluates system configurations against a CIS-style hardening baseline. It uses modules `/app/rule_parser.py`, `/app/inheritance_resolver.py`, `/app/exception_matcher.py`, `/app/severity_scorer.py`, `/app/scope_evaluator.py`, and `/app/report_formatter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/baseline_config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current baseline configuration but has bugs that cause incorrect compliance reports on other configurations. Find and fix the bugs so the pipeline handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure. In particular, preserve the active-resource-only scope evaluation (stopped resources are excluded from compliance checks since hardening controls apply exclusively to the active attack surface) and the child-overrides-parent rule precedence for profile inheritance conflicts (child profile rules take priority over parent rules with the same ID to prevent conflicting thresholds from propagating down the hierarchy).

The fixed pipeline will be tested on a different baseline configuration than the one at `/app/baseline_config.json`.

Output: `/app/output.json` — a JSON compliance report containing metadata, summary (overall_compliance, security_posture, risk_score, resources_assessed, rules_evaluated), compliance_scores (per_category scores with passing/failing/total counts, overall_score, category_weights), severity_distribution, critical_findings (severity >= 7), risk_score, waivers_applied (resource_id, rule_id, waiver_id, reason), scope_coverage, and detailed_results (resource_id, rule_id, status as pass/fail/waived, details).
