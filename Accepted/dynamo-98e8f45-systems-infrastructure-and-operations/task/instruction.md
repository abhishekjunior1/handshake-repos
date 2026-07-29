A Kubernetes pod scheduling simulator at `/app/pipeline.py` evaluates scheduling decisions for pending pods across a cluster. It uses modules `/app/resource_calculator.py`, `/app/affinity_evaluator.py`, `/app/taint_matcher.py`, `/app/priority_preemptor.py`, `/app/node_scorer.py`, and `/app/scheduler_reporter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The simulator produces correct output on the current configuration but has bugs that cause incorrect scheduling decisions on other cluster configurations. Find and fix the bugs so the simulator handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure. In particular, preserve the remaining-resource normalization in node scoring (the LeastAllocated strategy scores based on available capacity relative to remaining headroom, not total node capacity) and the exact-match toleration comparison (the Equal operator requires strict string equality for taint value matching, not pattern or wildcard matching).

The fixed simulator will be tested on different cluster configurations than the one at `/app/config.json`.

Output: `/app/output.json` — a JSON object with `scheduling_summary` (total_pods, scheduled, preempting, unschedulable, scheduling_rate), `pod_decisions` (array of per-pod decisions with pod_name, namespace, phase, selected_node, score_breakdown, filtered_nodes, preemption_attempted, preemption_victims), `node_placements` (per-node scheduled_pods and preempted_pods arrays), and `cluster_info` (total_nodes, scoring_strategy).
