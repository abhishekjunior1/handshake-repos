A graph analysis pipeline at `/app/pipeline.py` loads a directed property graph, computes betweenness centrality, PageRank influence scores, directed clustering coefficients, and influence spread metrics. It uses modules `/app/graph_loader.py`, `/app/path_analysis.py`, `/app/influence_scoring.py`, `/app/clustering.py`, `/app/graph_metrics.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/graph.json` and writes `/app/output.json`.

The graph data format is a JSON file with a `graph` object containing `nodes` (each with id, type, weight, properties) and directed `edges` (each with source, target, type, weight, properties), plus a `queries` object specifying parameters for each analysis stage.

The pipeline produces correct output on the current graph but has bugs that cause incorrect results on other graph structures. Find and fix the bugs so the pipeline handles all valid directed property graphs correctly.

Do not rewrite from scratch — preserve the existing module structure, the self-loop exclusion in clustering, and the (n-1)(n-2) normalization convention for directed betweenness centrality. The fixed pipeline will be tested on a different graph than the one at `/app/graph.json`.

Output: `/app/output.json` — a JSON object with fields: `graph_summary` (node_count, edge_count, type_distribution, density, reciprocity), `betweenness_centrality` (top_k list with node/score pairs, average_path_length), `pagerank` (top_k with node/score, iteration_count), `clustering` (coefficients per node, average, scc_sizes), and `influence_spread` (seeds, steps, total_influence, top_k with node/influence).
