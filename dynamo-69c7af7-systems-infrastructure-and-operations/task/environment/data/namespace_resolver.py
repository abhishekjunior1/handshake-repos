"""
Kubernetes namespace resolver module.

Resolves namespace selectors and performs label matching
for NetworkPolicy evaluation.
"""

from typing import Optional


class Namespace:
    """Represents a Kubernetes namespace with labels."""

    def __init__(self, name: str, labels: dict = None):
        self.name = name
        self.labels = labels or {}

    def has_label(self, key: str, value: str) -> bool:
        """Check if namespace has a specific label with given value."""
        return self.labels.get(key) == value

    def get_label(self, key: str) -> Optional[str]:
        """Get the value of a specific label."""
        return self.labels.get(key)

    def __repr__(self):
        return f"Namespace(name={self.name}, labels={self.labels})"


class Pod:
    """Represents a Kubernetes pod with labels and namespace."""

    def __init__(self, name: str, namespace: str, labels: dict = None, ip: str = ""):
        self.name = name
        self.namespace = namespace
        self.labels = labels or {}
        self.ip = ip

    def has_label(self, key: str, value: str) -> bool:
        """Check if pod has a specific label with given value."""
        return self.labels.get(key) == value

    def __repr__(self):
        return f"Pod(name={self.name}, namespace={self.namespace}, labels={self.labels})"


def match_labels(selector: dict, labels: dict) -> bool:
    """
    Check if labels satisfy a selector.
    Empty selector ({}) matches everything — this follows
    Kubernetes semantics where an empty selector selects all resources.
    """
    if not selector:
        return True
    for key, value in selector.items():
        if labels.get(key) != value:
            return False
    return True


def resolve_namespace_selector(
    selector_labels: Optional[dict],
    namespaces: list
) -> list:
    """
    Resolve a namespace selector to matching namespaces.

    An empty selector ({}) matches ALL namespaces per Kubernetes spec.
    A None selector means no namespace filtering (use pod's own namespace).
    """
    if selector_labels is None:
        return []
    return [ns for ns in namespaces if match_labels(selector_labels, ns.labels)]


def resolve_pod_selector(selector_labels: dict, pods: list, namespace: str = None) -> list:
    """
    Resolve a pod selector to matching pods.

    If namespace is provided, only match pods in that namespace.
    Empty selector ({}) matches all pods (in the given namespace if specified).
    """
    matched = []
    for pod in pods:
        if namespace and pod.namespace != namespace:
            continue
        if match_labels(selector_labels, pod.labels):
            matched.append(pod)
    return matched


def policy_selects_pod(policy_pod_selector: dict, pod: Pod) -> bool:
    """Check if a policy's pod selector matches a given pod."""
    return match_labels(policy_pod_selector, pod.labels)


def build_namespaces(config: dict) -> list:
    """Build Namespace objects from configuration data."""
    namespaces = []
    for ns_data in config.get("namespaces", []):
        ns = Namespace(
            name=ns_data["name"],
            labels=ns_data.get("labels", {})
        )
        namespaces.append(ns)
    return namespaces


def build_pods(config: dict) -> list:
    """Build Pod objects from configuration data."""
    pods = []
    for pod_data in config.get("pods", []):
        pod = Pod(
            name=pod_data["name"],
            namespace=pod_data["namespace"],
            labels=pod_data.get("labels", {}),
            ip=pod_data.get("ip", "")
        )
        pods.append(pod)
    return pods


def get_namespace_by_name(namespaces: list, name: str) -> Optional[Namespace]:
    """Find a namespace by name."""
    for ns in namespaces:
        if ns.name == name:
            return ns
    return None


def get_pods_in_namespace(pods: list, namespace: str) -> list:
    """Get all pods in a given namespace."""
    return [pod for pod in pods if pod.namespace == namespace]


def find_matching_namespaces_for_peer(peer_ns_selector: Optional[dict], namespaces: list) -> list:
    """
    Find namespaces matching a peer's namespace selector.

    Returns namespace names that match the selector.
    Empty selector {} matches all namespaces.
    None means no namespace constraint (same namespace).
    """
    if peer_ns_selector is None:
        return []
    matched = resolve_namespace_selector(peer_ns_selector, namespaces)
    return [ns.name for ns in matched]
