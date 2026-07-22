"""Graph metrics and statistics utilities.

Provides supplementary graph analysis functions including degree
distribution, density, centrality helpers, and structural properties.
"""


def compute_degree_distribution(graph):
    """Compute in-degree and out-degree for all nodes.

    Args:
        graph: PropertyGraph instance

    Returns:
        dict: {node_id: {'in_degree': int, 'out_degree': int}}
    """
    degrees = {nid: {'in_degree': 0, 'out_degree': 0} for nid in graph.nodes}

    for edge in graph.edges:
        degrees[edge.source]['out_degree'] += 1
        degrees[edge.target]['in_degree'] += 1

    return degrees


def compute_graph_density(graph):
    """Compute density of the directed graph.

    Density = edges / (n * (n-1)) for directed graphs.

    Args:
        graph: PropertyGraph instance

    Returns:
        float: Graph density in [0, 1]
    """
    n = graph.node_count
    if n <= 1:
        return 0.0
    return graph.edge_count / (n * (n - 1))


def compute_degree_centrality(graph):
    """Compute degree centrality for all nodes.

    For directed graphs, uses total degree (in + out) normalized by
    2*(n-1), the maximum possible total degree.

    Args:
        graph: PropertyGraph instance

    Returns:
        dict: {node_id: degree_centrality}
    """
    n = graph.node_count
    if n <= 1:
        return {nid: 0.0 for nid in graph.nodes}

    degrees = compute_degree_distribution(graph)
    max_degree = 2 * (n - 1)

    centrality = {}
    for nid, d in degrees.items():
        centrality[nid] = (d['in_degree'] + d['out_degree']) / max_degree

    return centrality


def find_sink_nodes(graph):
    """Find nodes with no outgoing edges.

    Args:
        graph: PropertyGraph instance

    Returns:
        list: Sorted node IDs with out_degree = 0
    """
    adjacency = graph.get_adjacency()
    return sorted([nid for nid in graph.nodes if len(adjacency.get(nid, [])) == 0])


def find_source_nodes(graph):
    """Find nodes with no incoming edges.

    Args:
        graph: PropertyGraph instance

    Returns:
        list: Sorted node IDs with in_degree = 0
    """
    reverse_adj = graph.get_reverse_adjacency()
    return sorted([nid for nid in graph.nodes if len(reverse_adj.get(nid, [])) == 0])


def compute_reciprocity(graph):
    """Compute edge reciprocity of the directed graph.

    Reciprocity = fraction of edges that have a corresponding reverse edge.

    Args:
        graph: PropertyGraph instance

    Returns:
        float: Reciprocity in [0, 1]
    """
    if graph.edge_count == 0:
        return 0.0

    edge_set = set()
    for edge in graph.edges:
        edge_set.add((edge.source, edge.target))

    reciprocal = sum(1 for s, t in edge_set if (t, s) in edge_set)
    return reciprocal / len(edge_set)


def compute_type_homophily(graph):
    """Compute homophily ratio - fraction of edges connecting same-type nodes.

    Args:
        graph: PropertyGraph instance

    Returns:
        float: Homophily ratio in [0, 1]
    """
    if graph.edge_count == 0:
        return 0.0

    same_type_edges = 0
    for edge in graph.edges:
        src = graph.get_node(edge.source)
        tgt = graph.get_node(edge.target)
        if src and tgt and src.type == tgt.type:
            same_type_edges += 1

    return same_type_edges / graph.edge_count


def compute_weighted_in_strength(graph, node_id):
    """Compute weighted in-strength (sum of incoming edge weights).

    Args:
        graph: PropertyGraph instance
        node_id: Target node

    Returns:
        float: Sum of incoming edge weights
    """
    reverse_adj = graph.get_reverse_adjacency()
    return sum(edge.weight for _, edge in reverse_adj.get(node_id, []))


def compute_weighted_out_strength(graph, node_id):
    """Compute weighted out-strength (sum of outgoing edge weights).

    Args:
        graph: PropertyGraph instance
        node_id: Target node

    Returns:
        float: Sum of outgoing edge weights
    """
    adjacency = graph.get_adjacency()
    return sum(edge.weight for _, edge in adjacency.get(node_id, []))
