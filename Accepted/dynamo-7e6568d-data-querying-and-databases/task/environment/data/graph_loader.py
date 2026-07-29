"""Graph data loader - parses directed property graphs from JSON format."""

import json
import sys


class Node:
    """Represents a node in the property graph."""

    def __init__(self, node_id, node_type, weight, properties):
        self.id = node_id
        self.type = node_type
        self.weight = weight
        self.properties = properties

    def __repr__(self):
        return f"Node({self.id}, type={self.type}, weight={self.weight})"

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)


class Edge:
    """Represents a directed weighted edge."""

    def __init__(self, source, target, edge_type, weight, properties):
        self.source = source
        self.target = target
        self.type = edge_type
        self.weight = weight
        self.properties = properties

    def __repr__(self):
        return f"Edge({self.source}->{self.target}, w={self.weight})"


class PropertyGraph:
    """Directed property graph with typed nodes and weighted edges."""

    def __init__(self, nodes, edges):
        self.nodes = {n.id: n for n in nodes}
        self.edges = edges
        self._adjacency = None
        self._reverse_adjacency = None
        self._all_neighbors = None

    @property
    def node_count(self):
        return len(self.nodes)

    @property
    def edge_count(self):
        return len(self.edges)

    def get_node(self, node_id):
        """Return node by ID, or None if not found."""
        return self.nodes.get(node_id)

    def get_adjacency(self):
        """Forward adjacency: node_id -> [(target_id, edge)]."""
        if self._adjacency is None:
            self._adjacency = {nid: [] for nid in self.nodes}
            for edge in self.edges:
                self._adjacency[edge.source].append((edge.target, edge))
        return self._adjacency

    def get_reverse_adjacency(self):
        """Reverse adjacency: node_id -> [(source_id, edge)]."""
        if self._reverse_adjacency is None:
            self._reverse_adjacency = {nid: [] for nid in self.nodes}
            for edge in self.edges:
                self._reverse_adjacency[edge.target].append((edge.source, edge))
        return self._reverse_adjacency

    def get_out_neighbors(self, node_id):
        """Return list of node IDs reachable via outgoing edges."""
        adj = self.get_adjacency()
        return [nid for nid, _ in adj.get(node_id, [])]

    def get_in_neighbors(self, node_id):
        """Return list of node IDs with edges pointing to this node."""
        rev = self.get_reverse_adjacency()
        return [nid for nid, _ in rev.get(node_id, [])]

    def get_all_neighbors(self, node_id):
        """Return union of in-neighbors and out-neighbors (undirected view)."""
        if self._all_neighbors is None:
            self._all_neighbors = {nid: set() for nid in self.nodes}
            for edge in self.edges:
                self._all_neighbors[edge.source].add(edge.target)
                self._all_neighbors[edge.target].add(edge.source)
        return list(self._all_neighbors.get(node_id, set()))

    def get_out_degree(self, node_id):
        """Return out-degree of a node."""
        adj = self.get_adjacency()
        return len(adj.get(node_id, []))

    def get_in_degree(self, node_id):
        """Return in-degree of a node."""
        rev = self.get_reverse_adjacency()
        return len(rev.get(node_id, []))

    def get_edge_weight(self, source, target):
        """Return weight of edge from source to target, or 0 if none."""
        adj = self.get_adjacency()
        for nid, edge in adj.get(source, []):
            if nid == target:
                return edge.weight
        return 0.0

    def get_outgoing_weight_sum(self, node_id):
        """Return sum of weights of all outgoing edges from a node."""
        adj = self.get_adjacency()
        return sum(edge.weight for _, edge in adj.get(node_id, []))

    def get_total_weight_sum(self):
        """Return sum of all edge weights in the graph."""
        return sum(edge.weight for edge in self.edges)

    def get_nodes_by_type(self, node_type):
        """Return all nodes of a given type."""
        return [n for n in self.nodes.values() if n.type == node_type]


def load_graph(filepath):
    """Load a property graph and query parameters from JSON."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading graph: {e}", file=sys.stderr)
        sys.exit(1)

    graph_data = data.get('graph', {})
    queries = data.get('queries', {})

    nodes = []
    for nd in graph_data.get('nodes', []):
        nodes.append(Node(
            node_id=nd['id'],
            node_type=nd.get('type', 'default'),
            weight=nd.get('weight', 1.0),
            properties=nd.get('properties', {})
        ))

    edges = []
    for ed in graph_data.get('edges', []):
        edges.append(Edge(
            source=ed['source'],
            target=ed['target'],
            edge_type=ed.get('type', 'default'),
            weight=ed.get('weight', 1.0),
            properties=ed.get('properties', {})
        ))

    return PropertyGraph(nodes, edges), queries
