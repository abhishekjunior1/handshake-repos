A zone-based firewall policy evaluation engine at `/app/pipeline.py` processes network packets through zone resolution, NAT translation, policy lookup, and stateful connection tracking to determine packet disposition. It uses modules `/app/zone_parser.py`, `/app/rule_engine.py`, `/app/nat_translator.py`, `/app/policy_resolver.py`, and `/app/flow_tracker.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/network_config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current configuration but has bugs that cause incorrect flow dispositions on other network configurations. Find and fix the bugs so the pipeline handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure and the first-match rule evaluation semantics. The fixed pipeline will be tested on a different network configuration than the one at `/app/network_config.json`.

Output: `/app/output.json` — a JSON object with `flow_results` (array of per-packet entries with packet_id, source_zone, dest_zone, action, nat_applied, connection_state, matched_rule) and `summary` (object with total_packets, permitted, denied, nat_translations, stateful_matches counts).
