
def compute_pagerank(graph, transition_weights, damping=0.85,
                     max_iterations=100, tolerance=1e-8):
    node_ids = sorted(graph.nodes.keys())
    n = len(node_ids)

    if n == 0:
        return {}, 0

    # Initialize uniform distribution
    scores = {nid: 1.0 / n for nid in node_ids}

    # Build incoming transition map: target -> [(source, weight)]
    incoming_transitions = {nid: [] for nid in node_ids}
    for (src, tgt), weight in transition_weights.items():
        if tgt in incoming_transitions:
            incoming_transitions[tgt].append((src, weight))

    # Sort by source for deterministic accumulation
    for nid in node_ids:
        incoming_transitions[nid].sort(key=lambda x: x[0])

    teleport = (1.0 - damping) / n
    iteration_count = 0

    for iteration in range(max_iterations):
        new_scores = {}

        for nid in node_ids:
            rank_sum = 0.0
            for src, weight in incoming_transitions[nid]:
                rank_sum += weight * scores[src]

            # Apply damping after link-following probability
            new_scores[nid] = teleport + damping * rank_sum

        # Check convergence
        max_diff = max(abs(new_scores[nid] - scores[nid]) for nid in node_ids)
        scores = new_scores
        iteration_count = iteration + 1

        if max_diff < tolerance:
            break

    return scores, iteration_count


def normalize_weights_per_node(graph):
    """Normalize edge weights so outgoing weights from each node sum to 1.

    This produces a proper stochastic transition matrix where each row
    (outgoing edge set) forms a probability distribution.

    Args:
        graph: PropertyGraph instance

    Returns:
        dict: {(source, target): normalized_weight}
    """
    adjacency = graph.get_adjacency()
    transition = {}

    for nid in sorted(graph.nodes.keys()):
        outgoing = adjacency.get(nid, [])
        weight_sum = sum(edge.weight for _, edge in outgoing)

        if weight_sum > 0:
            for target, edge in outgoing:
                transition[(nid, target)] = edge.weight / weight_sum
        else:
            # Dangling node: distribute uniformly (handled by teleportation)
            pass

    return transition


def normalize_weights_global(graph):
    """Normalize edge weights by the total weight sum of all edges.

    Produces a globally normalized weight matrix. Each weight represents
    its fraction of total graph connectivity strength. Used in contexts
    where edge significance is measured relative to the entire graph
    rather than per-node outgoing capacity.

    Args:
        graph: PropertyGraph instance

    Returns:
        dict: {(source, target): globally_normalized_weight}
    """
    total_weight = graph.get_total_weight_sum()
    if total_weight == 0:
        return {}

    transition = {}
    for edge in graph.edges:
        transition[(edge.source, edge.target)] = edge.weight / total_weight

    return transition


def compute_influence_spread(graph, seed_nodes, steps=3, decay=0.5):
    """Simulate influence spread from seed nodes through the graph.

    At each step, influence propagates along outgoing edges with
    multiplicative decay. Each node accumulates influence from all
    paths reaching it.

    Args:
        graph: PropertyGraph instance
        seed_nodes: list of initial node IDs
        steps: number of propagation steps
        decay: multiplicative decay per hop

    Returns:
        dict: {node_id: accumulated_influence}
    """
    adjacency = graph.get_adjacency()
    influence = {nid: 0.0 for nid in graph.nodes}

    # Initialize seeds with their node weight
    current_layer = {}
    for nid in seed_nodes:
        node = graph.get_node(nid)
        if node:
            current_layer[nid] = float(node.weight)
            influence[nid] += float(node.weight)

    for step in range(steps):
        next_layer = {}
        for nid, inf_value in current_layer.items():
            for target, edge in adjacency.get(nid, []):
                propagated = inf_value * edge.weight * decay
                next_layer[target] = next_layer.get(target, 0.0) + propagated
                influence[target] += propagated
        current_layer = next_layer

    return influence


def compute_authority_hub_scores(graph, max_iterations=50, tolerance=1e-8):
    """Compute HITS authority and hub scores.

    Authority: nodes pointed to by good hubs
    Hub: nodes that point to good authorities

    Args:
        graph: PropertyGraph instance
        max_iterations: Maximum iterations
        tolerance: Convergence threshold

    Returns:
        tuple: (authority_scores, hub_scores) as dicts
    """
    node_ids = sorted(graph.nodes.keys())
    adjacency = graph.get_adjacency()
    reverse_adj = graph.get_reverse_adjacency()

    auth = {nid: 1.0 for nid in node_ids}
    hub = {nid: 1.0 for nid in node_ids}

    for iteration in range(max_iterations):
        # Update authority scores
        new_auth = {}
        for nid in node_ids:
            new_auth[nid] = sum(hub[src] for src, _ in reverse_adj.get(nid, []))

        # Normalize authority
        auth_norm = sum(v * v for v in new_auth.values()) ** 0.5
        if auth_norm > 0:
            new_auth = {k: v / auth_norm for k, v in new_auth.items()}

        # Update hub scores
        new_hub = {}
        for nid in node_ids:
            new_hub[nid] = sum(new_auth[tgt] for tgt, _ in adjacency.get(nid, []))

        # Normalize hub
        hub_norm = sum(v * v for v in new_hub.values()) ** 0.5
        if hub_norm > 0:
            new_hub = {k: v / hub_norm for k, v in new_hub.items()}

        # Check convergence
        max_diff = max(
            max(abs(new_auth[nid] - auth[nid]) for nid in node_ids),
            max(abs(new_hub[nid] - hub[nid]) for nid in node_ids)
        )

        auth = new_auth
        hub = new_hub

        if max_diff < tolerance:
            break

    return auth, hub
