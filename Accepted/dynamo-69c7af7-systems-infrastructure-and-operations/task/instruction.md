A Kubernetes NetworkPolicy evaluation engine at `/app/pipeline.py` reads network policy definitions and traffic flows from `/app/network_config.json`, evaluates each flow against the policies, and writes results to `/app/output.json`. It uses modules `/app/policy_parser.py`, `/app/namespace_resolver.py`, `/app/traffic_matcher.py`, `/app/policy_engine.py`, `/app/connection_tracker.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/network_config.json` and writes `/app/output.json`.

The pipeline produces correct evaluation results on the current configuration but has bugs that cause incorrect verdicts on other configurations with multiple namespaces, overlapping policies, and egress rules. Find and fix the bugs so the engine handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure, the additive ingress rule evaluation (OR/union semantics across selecting policies), the empty-selector-matches-all semantics, and the namespace-level egress isolation model (the presence of any egress policy in a namespace triggers default-deny for all pods in that namespace, not just selected pods). The individual modules are implemented correctly — the bugs are in how `pipeline.py` orchestrates the evaluation. The fixed pipeline will be tested on a different configuration than the one at `/app/network_config.json`.

Output: `/app/output.json` — a JSON object with `config_name`, `summary` (total flows, allowed, denied counts), `evaluations` (array of per-flow entries with flow_id, final_verdict, ingress_verdict, egress_verdict, ingress_policy, egress_policy, and reason), and `connection_stats`.
