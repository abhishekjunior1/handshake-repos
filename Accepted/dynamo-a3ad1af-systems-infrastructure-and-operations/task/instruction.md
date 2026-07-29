A network configuration validation and routing pipeline at `/app/pipeline.py` loads a topology, validates interface addressing, computes OSPF routing tables, evaluates firewall ACL rules against traffic flows, detects misconfigurations (asymmetric routes, black holes, MTU mismatches), and generates an audit report.

It uses modules `/app/topology_loader.py`, `/app/address_validator.py`, `/app/route_computer.py`, `/app/acl_evaluator.py`, `/app/misconfig_detector.py`, and `/app/audit_reporter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` (which references `/app/topology.json`) and writes `/app/output.json`.

The pipeline produces correct output on the current topology and configuration but has bugs that cause incorrect results on other network topologies. Find and fix the bugs so the pipeline handles all valid topologies correctly, including networks with aggregated/tunneled links (where link bandwidth differs from interface bandwidth) and networks with broad subnets (/24 and larger). ACL rules that specify "interface_scope" as the destination match against the flow's destination host address as a /32 host route, not the receiving interface's subnet.

Do not rewrite from scratch — preserve the existing module structure and conventions. Preserve the integer OSPF cost convention and the administrative distance tie-breaking. The fixed pipeline will be tested on a different topology and configuration than the ones at `/app/topology.json` and `/app/config.json`.

Output: `/app/output.json` — a JSON object with keys: `summary` (overall network health status), `addressing_validation` (IP consistency checks), `routing_analysis` (OSPF costs and routing tables), `acl_evaluation` (per-flow permit/deny decisions with matched rules), `misconfiguration_report` (detected issues), and `topology_overview` (router/link summary).
