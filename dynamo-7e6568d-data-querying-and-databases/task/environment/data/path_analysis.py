"""Path analysis module - shortest paths and betweenness centrality.

Implements Brandes' algorithm for betweenness centrality on directed graphs,
using BFS-based shortest path counting and back-propagation of dependency
scores through predecessor lists.
"""

from collections import deque


def compute_shortest_path_counts(graph):
    """Compute pairwise shortest path distances and path counts via BFS.

    For each source node, runs BFS to find:
    - dist[source][target]: shortest path distance
    - sigma[source][target]: number of shortest paths from source to target
    - predecessors[source][target]: list of predecessors on shortest paths

    Args:
        graph: PropertyGraph instance

    Returns:
        tuple: (distances, sigma, predecessors)
            distances: dict[source][target] -> int (hop count)
            sigma: dict[source][target] -> int (path count)
            predecessors: dict[source][target] -> list[node_id]
    """
    adjacency = graph.get_adjacency()
    node_ids = sorted(graph.nodes.keys())

    distances = {}
    sigma = {}
    predecessors = {}

    for source in node_ids:
        dist = {nid: -1 for nid in node_ids}
        sig = {nid: 0 for nid in node_ids}
        pred = {nid: [] for nid in node_ids}

        dist[source] = 0
        sig[source] = 1
        queue = deque([source])

        while queue:
            v = queue.popleft()
            for w, _ in adjacency.get(v, []):
                # First discovery of w
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                # w found on a shortest path through v
                if dist[w] == dist[v] + 1:
                    sig[w] += sig[v]
                    pred[w].append(v)

        distances[source] = dist
        sigma[source] = sig
        predecessors[source] = pred

    return distances, sigma, predecessors


def compute_betweenness_centrality(graph, distances, sigma, predecessors):
    """Compute betweenness centrality using Brandes' back-propagation.

    For each source, processes nodes in reverse BFS order (non-increasing
    distance from source) and accumulates pair-dependency:

        delta_s(v) = sum over w in successors(v) on shortest paths from s:
                     (sigma[s][v] / sigma[s][w]) * (1 + delta_s(w))

    The betweenness of node v is: sum over all sources s of delta_s(v).

    The final values are normalized by dividing by (n-1)(n-2) for directed
    graphs to produce values in [0, 1].

    Args:
        graph: PropertyGraph instance
        distances: from compute_shortest_path_counts
        sigma: from compute_shortest_path_counts
        predecessors: from compute_shortest_path_counts

    Returns:
        dict: {node_id: betweenness_centrality_score}
    """
    node_ids = sorted(graph.nodes.keys())
    n = len(node_ids)
    betweenness = {nid: 0.0 for nid in node_ids}

    for source in node_ids:
        # Build order of nodes by distance from source (for back-propagation)
        ordered = sorted(
            [nid for nid in node_ids if distances[source][nid] >= 0],
            key=lambda x: distances[source][x]
        )

        delta = {nid: 0.0 for nid in node_ids}

        # Process in reverse order (farthest first)
        for w in reversed(ordered):
            if w == source:
                continue
            for v in predecessors[source][w]:
                # Brandes' formula: accumulate dependency
                delta[v] += (sigma[source][v] / sigma[source][w]) * (1.0 + delta[w])
            betweenness[w] += delta[w]

    # Normalize for directed graphs: (n-1)(n-2)
    normalization = (n - 1) * (n - 2) if n > 2 else 1.0
    for nid in node_ids:
        betweenness[nid] /= normalization

    return betweenness


def compute_pairwise_betweenness(graph, node_id, distances, sigma):
    """Compute betweenness for a single node using the formula approach.

    Betweenness(v) = sum over all s!=v, t!=v of:
        sigma(s,t|v) / sigma(s,t)

    where sigma(s,t|v) is the number of shortest paths from s to t
    passing through v. A node v is on a shortest path from s to t
    if and only if dist(s,v) + dist(v,t) == dist(s,t).

    When v is on the shortest path: sigma(s,t|v) = sigma(s,v) * sigma(v,t)

    Args:
        graph: PropertyGraph instance
        node_id: Node to compute betweenness for
        distances: from compute_shortest_path_counts
        sigma: from compute_shortest_path_counts

    Returns:
        float: Raw betweenness centrality (unnormalized)
    """
    node_ids = sorted(graph.nodes.keys())
    betweenness = 0.0

    for s in node_ids:
        if s == node_id:
            continue
        for t in node_ids:
            if t == node_id or t == s:
                continue
            if sigma[s][t] == 0:
                continue
            # Check if node_id is on a shortest path from s to t
            d_sv = distances[s][node_id]
            d_vt = distances[node_id][t]
            d_st = distances[s][t]
            if d_sv < 0 or d_vt < 0 or d_st < 0:
                continue
            if d_sv + d_vt == d_st:
                # v is on a shortest s->t path
                paths_through_v = sigma[s][node_id] * sigma[node_id][t]
                betweenness += paths_through_v / sigma[s][t]

    return betweenness


def find_shortest_path(graph, source, target):
    """Find a single shortest path from source to target via BFS.

    Args:
        graph: PropertyGraph instance
        source: Source node ID
        target: Target node ID

    Returns:
        list: Node IDs forming the path, or empty list if unreachable
    """
    if source == target:
        return [source]

    adjacency = graph.get_adjacency()
    visited = {source}
    queue = deque([(source, [source])])

    while queue:
        current, path = queue.popleft()
        for neighbor, _ in adjacency.get(current, []):
            if neighbor == target:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return []


def compute_average_path_length(graph, distances):
    """Compute average shortest path length across all reachable pairs.

    Args:
        graph: PropertyGraph instance
        distances: from compute_shortest_path_counts

    Returns:
        float: Average path length (excluding unreachable pairs)
    """
    node_ids = sorted(graph.nodes.keys())
    total_dist = 0
    pair_count = 0

    for s in node_ids:
        for t in node_ids:
            if s == t:
                continue
            d = distances[s][t]
            if d > 0:
                total_dist += d
                pair_count += 1

    return total_dist / pair_count if pair_count > 0 else 0.0
