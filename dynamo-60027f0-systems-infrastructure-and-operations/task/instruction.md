A network packet processing pipeline at `/app/network.py` forwards packets through DNS resolution, NAT translation, firewall policy evaluation, route selection, QoS classification, and load balancing. It uses modules `/app/dns.py`, `/app/router.py`, `/app/firewall.py`, `/app/loadbalancer.py`, and `/app/config.py`.

Run it with `python3 /app/network.py /app/config.json`. It reads `/app/config.json` and writes `/app/output.json`.

The pipeline produces correct forwarding decisions on the current configuration but has bugs that cause incorrect results on other configurations. Find and fix the bugs so the pipeline handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure, the TTL hop-count decrement before route lookup, and the consistent-hash load balancer selection. The fixed pipeline will be tested on a different configuration than the one at `/app/config.json`.

Output: `/app/output.json` — JSON object with a "results" array. Each result contains the packet's forwarding decision through each pipeline stage: DNS resolution, NAT translation, firewall action with matched rule, routing with next-hop, QoS classification with DSCP marking, and load balancer backend. Packets denied by firewall or expired by TTL terminate early with status "denied" or "dropped".
