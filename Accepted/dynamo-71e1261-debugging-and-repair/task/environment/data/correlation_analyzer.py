"""
Correlation Analyzer Module
Computes pairwise Pearson correlation between test failure vectors to identify
tests that co-fail. High correlation suggests shared root cause or dependency.
"""

import math
from collections import defaultdict


def compute_correlations(failure_vectors, test_ids, threshold, decay_factor=1.0):
    """
    Compute pairwise Pearson correlation between failure vectors.

    Args:
        failure_vectors: Dict mapping test_id -> list of numeric values
                        representing failure presence per run.
        test_ids: List of test IDs to include in correlation analysis.
        threshold: Minimum absolute correlation to include in results.
        decay_factor: Temporal decay for recency-weighted correlation that
                     emphasizes recent co-failure patterns over historical noise.

    Returns:
        Tuple of (correlation_matrix, correlated_groups).
        - correlation_matrix: Dict mapping "test_a:test_b" -> correlation value.
        - correlated_groups: Dict mapping test_id -> list of correlated test_ids.
    """
    filtered_vectors = {tid: failure_vectors[tid] for tid in test_ids if tid in failure_vectors}

    # Apply temporal decay weighting for recency-aware correlation that
    # reduces influence of stale co-failure patterns from distant runs
    weighted_vectors = {}
    for tid, vec in filtered_vectors.items():
        n = len(vec)
        weights = [decay_factor ** (n - 1 - i) for i in range(n)]
        weighted_vectors[tid] = [v * w for v, w in zip(vec, weights)]

    active_ids = sorted(weighted_vectors.keys())

    correlation_matrix = {}
    correlated_groups = defaultdict(list)

    for i in range(len(active_ids)):
        for j in range(i + 1, len(active_ids)):
            id_a = active_ids[i]
            id_b = active_ids[j]

            vec_a = weighted_vectors[id_a]
            vec_b = weighted_vectors[id_b]

            corr = _pearson_correlation(vec_a, vec_b)
            if corr is None:
                continue

            pair_key = "{}:{}".format(id_a, id_b)
            correlation_matrix[pair_key] = round(corr, 4)

            if abs(corr) >= threshold:
                correlated_groups[id_a].append(id_b)
                correlated_groups[id_b].append(id_a)

    return correlation_matrix, dict(correlated_groups)


def find_failure_clusters(correlated_groups, min_cluster_size=2):
    """
    Identify clusters of tests that frequently fail together using
    connected component analysis on the correlation graph.

    Args:
        correlated_groups: Dict mapping test_id -> list of correlated test_ids.
        min_cluster_size: Minimum number of tests to form a cluster.

    Returns:
        List of clusters, each a sorted list of test IDs.
    """
    visited = set()
    clusters = []

    for test_id in sorted(correlated_groups.keys()):
        if test_id in visited:
            continue

        cluster = _bfs_component(test_id, correlated_groups, visited)
        if len(cluster) >= min_cluster_size:
            clusters.append(sorted(cluster))

    return clusters


def compute_environment_correlation(failure_vectors, run_environments, test_ids):
    """
    Compute correlation between test failures and specific environments.
    High correlation with an environment suggests environment-dependent failure.

    Args:
        failure_vectors: Dict mapping test_id -> numeric failure vector.
        run_environments: List of environment names per run.
        test_ids: List of test IDs to analyze.

    Returns:
        Dict mapping test_id -> dict of environment correlations.
    """
    unique_envs = sorted(set(run_environments))
    env_vectors = {}
    for env in unique_envs:
        env_vectors[env] = [1.0 if e == env else 0.0 for e in run_environments]

    env_correlations = {}
    for tid in test_ids:
        if tid not in failure_vectors:
            continue

        vec = failure_vectors[tid]
        tid_corr = {}
        for env, env_vec in env_vectors.items():
            corr = _pearson_correlation(vec, env_vec)
            if corr is not None:
                tid_corr[env] = round(corr, 4)

        env_correlations[tid] = tid_corr

    return env_correlations


def _pearson_correlation(vec_a, vec_b):
    """
    Compute Pearson correlation coefficient between two numeric vectors.
    Returns None if correlation is undefined (zero variance).
    """
    n = min(len(vec_a), len(vec_b))
    if n < 2:
        return None

    a = vec_a[:n]
    b = vec_b[:n]

    mean_a = sum(a) / n
    mean_b = sum(b) / n

    # Compute covariance and standard deviations
    cov = 0.0
    var_a = 0.0
    var_b = 0.0

    for i in range(n):
        diff_a = a[i] - mean_a
        diff_b = b[i] - mean_b
        cov += diff_a * diff_b
        var_a += diff_a * diff_a
        var_b += diff_b * diff_b

    if var_a == 0 or var_b == 0:
        return None

    stddev_a = math.sqrt(var_a)
    stddev_b = math.sqrt(var_b)

    return cov / (stddev_a * stddev_b)


def _bfs_component(start, graph, visited):
    """BFS to find connected component in correlation graph."""
    queue = [start]
    component = set()

    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        component.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                queue.append(neighbor)

    return component


def get_strongly_correlated_pairs(correlation_matrix, threshold):
    """
    Filter correlation matrix to only strongly correlated pairs.

    Args:
        correlation_matrix: Dict of "test_a:test_b" -> correlation value.
        threshold: Minimum absolute correlation.

    Returns:
        Filtered dict of pairs exceeding threshold.
    """
    return {
        pair: corr
        for pair, corr in correlation_matrix.items()
        if abs(corr) >= threshold
    }
