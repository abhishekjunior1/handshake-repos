A service mesh traffic routing pipeline at `/app/pipeline.py` processes requests through route resolution, backend health checking, load balancing, circuit breaking, and retry handling. It uses modules `/app/service_registry.py`, `/app/load_balancer.py`, `/app/circuit_breaker.py`, `/app/retry_handler.py`, and `/app/route_resolver.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/mesh_config.json` and writes `/app/output.json`.

The pipeline produces correct routing decisions on the current configuration but has bugs that cause incorrect backend selection, delivery status, and retry accounting on other configurations with multiple services, backends, and failure states. Find and fix the bugs so the pipeline handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure, the descending route priority evaluation order, and the Knuth multiplicative hash ring distribution. The fixed pipeline will be tested on a different configuration than the one at `/app/mesh_config.json`.

Output: `/app/output.json` — a JSON object with `pipeline_version`, `current_time`, `total_requests`, and `results` (array of per-request entries with request_id, source, destination, status, routed_to, route_rule, remaining_retries, and attempts).
