"""Clustering analysis module - directed clustering coefficient and communities.

Implements directed clustering coefficient computation and connected component
detection for property graphs. The directed clustering coefficient measures
how tightly interconnected a node's neighbors are via directed edges.
"""


def compute_directed_clustering_coefficient(graph, node_id, neighbor_ids):
    """Compute directed clustering coefficient for a node given its neighborhood.

    The directed clustering coefficient of a node v with neighborhood N is:

        C(v) = |{(u, w) : u, w in N, edge(u, w) exists}| / (|N| * (|N| - 1))

    This counts the fraction of possible directed edges among the neighbors
    that actually exist. For directed graphs, the maximum is |N|*(|N|-1)
    since both (u,w) and (w,u) are distinct potential edges.

    Args:
        graph: PropertyGraph instance
        node_id: The node whose coefficient to compute
        neighbor_ids: List of neighbor node IDs to use as the neighborhood

    Returns:
        float: Clustering coefficient in [0, 1]
    """
    neighbors = set(neighbor_ids)
    neighbors.discard(node_id)  # Exclude self-loops from neighborhood

    k = len(neighbors)
    if k < 2:
        return 0.0

    # Count directed edges among neighbors
    adjacency = graph.get_adjacency()
    edge_count = 0
    for u in neighbors:
        for target, _ in adjacency.get(u, []):
            if target in neighbors and target != u:
                edge_count += 1

    # Maximum possible directed edges among k nodes
    max_edges = k * (k - 1)

    return edge_count / max_edges


def compute_graph_clustering(graph, neighborhoods):
    """Compute clustering coefficient for all nodes given their neighborhoods.

    Args:
        graph: PropertyGraph instance
        neighborhoods: dict[node_id] -> list[neighbor_ids]
            The neighborhood definition for each node

    Returns:
        dict: {node_id: clustering_coefficient}
    """
    coefficients = {}
    for nid in sorted(graph.nodes.keys()):
        neighbors = neighborhoods.get(nid, [])
        coefficients[nid] = compute_directed_clustering_coefficient(
            graph, nid, neighbors
        )
    return coefficients


def compute_average_clustering(coefficients):
    """Compute the average clustering coefficient across all nodes.

    Args:
        coefficients: dict[node_id] -> clustering_coefficient

    Returns:
        float: Average clustering coefficient
    """
    if not coefficients:
        return 0.0
    return sum(coefficients.values()) / len(coefficients)


def find_connected_components(graph):
    """Find weakly connected components using union-find.

    Two nodes are in the same weakly connected component if they are
    connected by any path ignoring edge direction.

    Args:
        graph: PropertyGraph instance

    Returns:
        list: List of sets, each containing node IDs in one component
    """
    parent = {nid: nid for nid in graph.nodes}
    rank = {nid: 0 for nid in graph.nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx == ry:
            return
        if rank[rx] < rank[ry]:
            parent[rx] = ry
        elif rank[rx] > rank[ry]:
            parent[ry] = rx
        else:
            parent[ry] = rx
            rank[rx] += 1

    for edge in graph.edges:
        union(edge.source, edge.target)

    components = {}
    for nid in graph.nodes:
        root = find(nid)
        if root not in components:
            components[root] = set()
        components[root].add(nid)

    return list(components.values())


def find_strongly_connected_components(graph):
    """Find strongly connected components using Kosaraju's algorithm.

    A strongly connected component is a maximal set of nodes where
    every node can reach every other node following edge direction.

    Args:
        graph: PropertyGraph instance

    Returns:
        list: List of sets, each containing node IDs in one SCC
    """
    adjacency = graph.get_adjacency()
    reverse_adj = graph.get_reverse_adjacency()
    node_ids = sorted(graph.nodes.keys())

    # First pass: DFS on forward graph, record finish order
    visited = set()
    finish_order = []

    for start in node_ids:
        if start in visited:
            continue
        stack = [(start, False)]
        while stack:
            node, processed = stack.pop()
            if processed:
                finish_order.append(node)
                continue
            if node in visited:
                continue
            visited.add(node)
            stack.append((node, True))
            for neighbor, _ in adjacency.get(node, []):
                if neighbor not in visited:
                    stack.append((neighbor, False))

    # Second pass: DFS on reverse graph in reverse finish order
    visited2 = set()
    components = []

    for node in reversed(finish_order):
        if node in visited2:
            continue
        component = set()
        stack = [node]
        while stack:
            current = stack.pop()
            if current in visited2:
                continue
            visited2.add(current)
            component.add(current)
            for neighbor, _ in reverse_adj.get(current, []):
                if neighbor not in visited2:
                    stack.append(neighbor)
        components.append(component)

    return components


def compute_modularity(graph, communities):
    """Compute Newman-Girvan modularity for a given community partition.

    Q = (1/m) * sum_{communities} sum_{i,j in C} [A(i,j) - k_i*k_j/(2m)]

    For directed graphs, uses in/out degree products.

    Args:
        graph: PropertyGraph instance
        communities: list of sets of node IDs

    Returns:
        float: Modularity score in [-0.5, 1]
    """
    m = graph.edge_count
    if m == 0:
        return 0.0

    # Build node-to-community mapping
    node_community = {}
    for idx, community in enumerate(communities):
        for nid in community:
            node_community[nid] = idx

    adjacency = graph.get_adjacency()
    modularity = 0.0

    for nid in graph.nodes:
        out_degree = graph.get_out_degree(nid)
        comm_i = node_community.get(nid, -1)

        for target, _ in adjacency.get(nid, []):
            in_degree_target = graph.get_in_degree(target)
            comm_j = node_community.get(target, -2)

            if comm_i == comm_j:
                modularity += 1.0 - (out_degree * in_degree_target) / m

    return modularity / m
