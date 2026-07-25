"""Graph analysis pipeline - orchestrates path, influence, and clustering analyses."""

import sys
from graph_loader import load_graph
from path_analysis import (compute_shortest_path_counts,
                           compute_pairwise_betweenness,
                           compute_average_path_length)
from influence_scoring import (compute_pagerank, normalize_weights_global,
                               normalize_weights_per_node,
                               compute_influence_spread)
from clustering import (compute_directed_clustering_coefficient,
                        compute_graph_clustering, compute_average_clustering,
                        find_strongly_connected_components)
from graph_metrics import (compute_degree_distribution, compute_graph_density,
                           compute_reciprocity, compute_type_homophily)
from report_generator import generate_report


def run_pipeline(graph_path, output_path):
    """Execute the full graph analysis pipeline."""
    graph, queries = load_graph(graph_path)
    results = {}

    # --- Graph Summary ---
    type_dist = {}
    for node in graph.nodes.values():
        type_dist[node.type] = type_dist.get(node.type, 0) + 1

    degrees = compute_degree_distribution(graph)
    density = compute_graph_density(graph)
    reciprocity = compute_reciprocity(graph)

    results['graph_summary'] = {
        'node_count': graph.node_count,
        'edge_count': graph.edge_count,
        'type_distribution': type_dist,
        'density': round(density, 6),
        'reciprocity': round(reciprocity, 6)
    }

    # --- Betweenness Centrality Analysis ---
    centrality_query = queries.get('centrality', {})
    if centrality_query:
        top_k = centrality_query.get('top_k', 3)

        distances, sigma, predecessors = compute_shortest_path_counts(graph)

        # Compute betweenness for each node using the pairwise formula
        betweenness = {}
        node_ids = sorted(graph.nodes.keys())
        n = len(node_ids)

        for v in node_ids:
            raw_bc = 0.0
            for s in node_ids:
                if s == v:
                    continue
                for t in node_ids:
                    if t == v or t == s:
                        continue
                    if sigma[s][t] == 0:
                        continue
                    # Count paths from s to t through v: node must be reachable
                    # from s and able to reach t for path contribution
                    d_sv = distances[s][v]
                    d_vt = distances[v][t]
                    if d_sv < 0 or d_vt < 0:
                        continue
                    paths_through_v = sigma[s][v] * sigma[v][t]
                    raw_bc += paths_through_v / sigma[s][t]

            # Normalize for directed graphs
            normalization = (n - 1) * (n - 2) if n > 2 else 1.0
            betweenness[v] = raw_bc / normalization

        avg_path = compute_average_path_length(graph, distances)

        sorted_bc = sorted(betweenness.items(), key=lambda x: (-x[1], x[0]))
        results['betweenness_centrality'] = {
            'top_k': [{'node': nid, 'score': round(score, 6)}
                      for nid, score in sorted_bc[:top_k]],
            'average_path_length': round(avg_path, 6)
        }

    # --- PageRank Influence Scoring ---
    pagerank_query = queries.get('pagerank', {})
    if pagerank_query:
        damping = pagerank_query.get('damping', 0.85)
        max_iterations = pagerank_query.get('max_iterations', 100)
        top_k = pagerank_query.get('top_k', 3)

        # Normalize edge weights for transition probability computation
        transition_weights = normalize_weights_global(graph)

        scores, iteration_count = compute_pagerank(
            graph, transition_weights,
            damping=damping,
            max_iterations=max_iterations
        )

        sorted_pr = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        results['pagerank'] = {
            'top_k': [{'node': nid, 'score': round(score, 6)}
                      for nid, score in sorted_pr[:top_k]],
            'iteration_count': iteration_count
        }

    # --- Directed Clustering Coefficient ---
    clustering_query = queries.get('clustering', {})
    if clustering_query:
        # Collect neighborhood for each node: use all connections (in + out)
        # for the neighborhood definition since influence flows both ways
        neighborhoods = {}
        for nid in sorted(graph.nodes.keys()):
            neighborhoods[nid] = graph.get_all_neighbors(nid)

        coefficients = compute_graph_clustering(graph, neighborhoods)
        avg_clustering = compute_average_clustering(coefficients)

        # Find strongly connected components for structural context
        sccs = find_strongly_connected_components(graph)
        scc_sizes = sorted([len(c) for c in sccs], reverse=True)

        sorted_cc = sorted(coefficients.items(), key=lambda x: (-x[1], x[0]))
        results['clustering'] = {
            'coefficients': {nid: round(val, 6) for nid, val in sorted_cc},
            'average': round(avg_clustering, 6),
            'scc_sizes': scc_sizes
        }

    # --- Influence Spread Analysis ---
    spread_query = queries.get('influence_spread', {})
    if spread_query:
        seed_nodes = spread_query.get('seeds', [])
        steps = spread_query.get('steps', 3)
        decay = spread_query.get('decay', 0.5)

        influence = compute_influence_spread(graph, seed_nodes, steps, decay)

        top_k = spread_query.get('top_k', 5)
        sorted_inf = sorted(influence.items(), key=lambda x: (-x[1], x[0]))

        results['influence_spread'] = {
            'seeds': seed_nodes,
            'steps': steps,
            'total_influence': round(sum(influence.values()), 6),
            'top_k': [{'node': nid, 'influence': round(val, 6)}
                      for nid, val in sorted_inf[:top_k]]
        }

    # Generate output report
    generate_report(results, output_path)
    print(f"Analysis complete. Output: {output_path}")


if __name__ == '__main__':
    graph_path = '/app/graph.json'
    output_path = '/app/output.json'

    if len(sys.argv) > 1:
        graph_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]

    run_pipeline(graph_path, output_path)
