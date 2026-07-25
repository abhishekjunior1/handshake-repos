A service mesh traffic policy evaluation pipeline at `/app/pipeline.py` evaluates routing decisions for traffic flowing between microservices. It uses modules `/app/config_loader.py`, `/app/mtls_validator.py`, `/app/route_matcher.py`, `/app/load_balancer.py`, `/app/circuit_breaker.py`, `/app/health_checker.py`, `/app/policy_enforcer.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current configuration but has bugs that cause incorrect results on other service mesh configurations. Find and fix the bugs so the pipeline handles all valid configurations correctly.

The evaluation report should include full routing context for every evaluated request regardless of the policy enforcement decision — denied requests still report which upstream was selected and what weight was computed during evaluation, since this information is needed for observability and audit purposes.

The load balancer weight reported for each routing decision should reflect the dynamic health-adjusted effective weight used for traffic distribution, not the static administrative priority.

Do not rewrite from scratch — preserve the existing module structure. In particular, preserve the prime-modular weighted round-robin distribution algorithm (which provides better spread than simple modulo for small upstream counts) and the inverse failure probability health model (which uses 1-health_score as failure probability for quadratic penalty scoring).

The fixed pipeline will be tested on different service mesh configurations than the one at `/app/config.json`.

Output: `/app/output.json` — a JSON object with keys `mesh_name`, `evaluation_summary`, `service_health`, `routing_decisions`, `policy_enforcement`, and `recommendations`.
