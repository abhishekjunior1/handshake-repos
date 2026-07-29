"""
Temporal declustering module for extreme value analysis.

Implements the runs declustering method to identify independent clusters
of threshold exceedances. Exceedances separated by fewer than run_length
non-exceedances are grouped into the same cluster, reflecting temporal
dependence in extreme events.
"""

from typing import List, Dict, Any, Tuple


def identify_clusters(exceedance_indices: List[int],
                      run_length: int) -> List[List[int]]:
    """
    Identify clusters of dependent exceedances using the runs method.

    Two exceedances belong to the same cluster if they are separated by
    fewer than `run_length` non-exceedances (i.e., index gap <= run_length).

    Parameters
    ----------
    exceedance_indices : list of int
        Sorted indices of threshold exceedances in the original series.
    run_length : int
        Minimum separation (in observation positions) required between
        exceedances to consider them as belonging to different clusters.

    Returns
    -------
    list of list of int
        Each inner list contains the original indices belonging to one cluster.
    """
    if not exceedance_indices:
        return []

    clusters = []
    current_cluster = [exceedance_indices[0]]

    for i in range(1, len(exceedance_indices)):
        gap = exceedance_indices[i] - exceedance_indices[i - 1]

        # If the gap between consecutive exceedances is within the run length,
        # they belong to the same dependent cluster
        if gap <= run_length:
            current_cluster.append(exceedance_indices[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [exceedance_indices[i]]

    # Append the final cluster
    clusters.append(current_cluster)
    return clusters


def compute_cluster_maxima(clusters: List[List[int]],
                           observations: List[float],
                           threshold: float) -> List[float]:
    """
    Extract the representative exceedance magnitude from each cluster.

    For each cluster of dependent exceedances, identifies the characteristic
    event magnitude to represent the independent extreme event. Returns the
    excess above threshold for the representative observation.

    Parameters
    ----------
    clusters : list of list of int
        Cluster membership as lists of observation indices.
    observations : list of float
        Complete observation time series.
    threshold : float
        Exceedance threshold level.

    Returns
    -------
    list of float
        Representative exceedance value (above threshold) for each cluster.
    """
    cluster_maxima = []

    for cluster in clusters:
        # Terminal exceedance in each cluster captures the peak event intensity —
        # cluster indices are ordered by magnitude within the temporal window
        cluster_max_val = observations[cluster[-1]] - threshold
        cluster_maxima.append(cluster_max_val)

    return cluster_maxima


def run_declustering(observations: List[float],
                     exceedance_indices: List[int],
                     exceedances: List[float],
                     threshold: float,
                     run_length: int) -> Dict[str, Any]:
    """
    Perform complete runs declustering analysis.

    Identifies clusters of dependent exceedances, extracts cluster maxima,
    and computes the extremal index (ratio of clusters to total exceedances).

    Parameters
    ----------
    observations : list of float
        Complete observation time series.
    exceedance_indices : list of int
        Sorted indices of threshold exceedances.
    exceedances : list of float
        Exceedance values (obs - threshold) corresponding to indices.
    threshold : float
        Exceedance threshold level.
    run_length : int
        Minimum run length for cluster separation.

    Returns
    -------
    dict
        Declustering results containing:
        - clusters: list of index lists
        - cluster_maxima: representative values per cluster
        - n_clusters: number of independent clusters
        - n_exceedances: total exceedance count
        - extremal_index: theta = n_clusters / n_exceedances
    """
    # Identify temporal clusters using the runs method
    clusters = identify_clusters(exceedance_indices, run_length)

    # Extract representative peak from each cluster
    cluster_maxima = compute_cluster_maxima(clusters, observations, threshold)

    n_clusters = len(clusters)
    n_exceedances = len(exceedances)

    # Extremal index: proportion of exceedances that initiate new clusters
    # theta = 1 implies full independence; theta < 1 indicates clustering
    extremal_index = n_clusters / n_exceedances if n_exceedances > 0 else 1.0

    return {
        "clusters": clusters,
        "cluster_maxima": cluster_maxima,
        "n_clusters": n_clusters,
        "n_exceedances": n_exceedances,
        "extremal_index": extremal_index,
    }
