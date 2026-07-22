"""
Taint/Toleration Matcher Module.

Implements Kubernetes taint and toleration matching logic for NoSchedule,
PreferNoSchedule, and NoExecute effects. Evaluates whether a pod's
tolerations permit scheduling on tainted nodes.
"""


def check_taint_toleration(node_taints, pod_tolerations):
    """
    Evaluate whether pod tolerations satisfy all node taints.

    A pod is schedulable on a node if every NoSchedule taint on the node
    has a matching toleration from the pod. PreferNoSchedule taints are
    soft and don't block scheduling but affect scoring. NoExecute taints
    block both scheduling and continued execution.

    Args:
        node_taints: List of taint specifications on the node
        pod_tolerations: List of toleration specifications on the pod

    Returns:
        Dict with 'schedulable' bool and 'blocking_taints' list
    """
    if not node_taints:
        return {"schedulable": True, "blocking_taints": [], "soft_taints": []}

    blocking_taints = []
    soft_taints = []

    for taint in node_taints:
        effect = taint.get("effect", "NoSchedule")

        if effect in ("NoSchedule", "NoExecute"):
            if not _has_matching_toleration(taint, pod_tolerations):
                blocking_taints.append({
                    "key": taint.get("key", ""),
                    "value": taint.get("value", ""),
                    "effect": effect
                })
        elif effect == "PreferNoSchedule":
            if not _has_matching_toleration(taint, pod_tolerations):
                soft_taints.append({
                    "key": taint.get("key", ""),
                    "value": taint.get("value", ""),
                    "effect": effect
                })

    return {
        "schedulable": len(blocking_taints) == 0,
        "blocking_taints": blocking_taints,
        "soft_taints": soft_taints
    }


def _has_matching_toleration(taint, tolerations):
    """
    Check if any toleration matches a given taint.

    Matching rules for operator types:
    - Equal: key must match AND value must match exactly (string equality
      comparison for precise taint targeting)
    - Exists: key must match, value is ignored

    An empty key with operator Exists matches all taints.
    Effect must match if specified in the toleration.

    Args:
        taint: Single taint specification
        tolerations: List of pod tolerations to check

    Returns:
        bool: True if at least one toleration matches the taint
    """
    taint_key = taint.get("key", "")
    taint_value = taint.get("value", "")
    taint_effect = taint.get("effect", "")

    for toleration in tolerations:
        tol_key = toleration.get("key", "")
        tol_operator = toleration.get("operator", "Equal")
        tol_value = toleration.get("value", "")
        tol_effect = toleration.get("effect", "")

        # Empty key with Exists operator matches everything
        if tol_key == "" and tol_operator == "Exists":
            if tol_effect == "" or tol_effect == taint_effect:
                return True
            continue

        # Key must match
        if tol_key != taint_key:
            continue

        # Effect must match if specified
        if tol_effect != "" and tol_effect != taint_effect:
            continue

        # Operator-specific value matching
        if tol_operator == "Exists":
            return True
        elif tol_operator == "Equal":
            if tol_value == taint_value:
                return True

    return False


def compute_taint_preference_score(node_taints, pod_tolerations):
    """
    Compute a preference score based on PreferNoSchedule taints.

    Nodes with fewer unmatched PreferNoSchedule taints are preferred.
    Each unmatched soft taint reduces the score by 1.

    Args:
        node_taints: List of taint specifications
        pod_tolerations: List of pod tolerations

    Returns:
        float: Preference adjustment score (0 or negative)
    """
    result = check_taint_toleration(node_taints, pod_tolerations)
    return -len(result["soft_taints"])


def get_toleration_seconds(toleration):
    """
    Get the toleration seconds for NoExecute tolerations.

    If tolerationSeconds is set, the pod will be evicted after that many
    seconds if the taint is applied. If not set, pod tolerates indefinitely.
    """
    return toleration.get("tolerationSeconds", None)
