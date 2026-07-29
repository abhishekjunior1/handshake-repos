#!/usr/bin/env python3
"""Solution script - patches bugs in the graph analysis pipeline."""

import subprocess
import sys


def patch_file(filepath, replacements):
    """Apply string replacements to a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    for old, new in replacements:
        if old not in content:
            print(f"WARNING: Pattern not found in {filepath}: {old[:60]}...")
            continue
        content = content.replace(old, new)
    
    with open(filepath, 'w') as f:
        f.write(content)


def fix_bug1_betweenness_constraint():
    """Fix Bug 1: Add shortest-path membership check to betweenness computation.
    
    The pipeline counts paths through node v without verifying that v
    actually lies on a shortest path from s to t (d_sv + d_vt == d_st).
    On a linear graph every intermediate node IS on the shortest path,
    but on graphs with cycles/alternate routes, non-shortest paths get counted.
    """
    patch_file('/app/pipeline.py', [
        (
            '                    d_sv = distances[s][v]\n'
            '                    d_vt = distances[v][t]\n'
            '                    if d_sv < 0 or d_vt < 0:\n'
            '                        continue\n'
            '                    paths_through_v = sigma[s][v] * sigma[v][t]',
            '                    d_sv = distances[s][v]\n'
            '                    d_vt = distances[v][t]\n'
            '                    d_st = distances[s][t]\n'
            '                    if d_sv < 0 or d_vt < 0:\n'
            '                        continue\n'
            '                    if d_sv + d_vt != d_st:\n'
            '                        continue\n'
            '                    paths_through_v = sigma[s][v] * sigma[v][t]'
        ),
    ])


def fix_bug2_pagerank_normalization():
    """Fix Bug 2: Use per-node normalization for proper stochastic transitions.
    
    Global normalization divides each edge weight by the total weight sum
    of ALL edges, producing non-stochastic transitions. Per-node normalization
    makes each node's outgoing weights sum to 1 (proper transition matrix).
    """
    patch_file('/app/pipeline.py', [
        (
            '        # Normalize edge weights for transition probability computation\n'
            '        transition_weights = normalize_weights_global(graph)',
            '        # Normalize edge weights for transition probability computation\n'
            '        transition_weights = normalize_weights_per_node(graph)'
        ),
    ])


def fix_bug3_clustering_neighborhood():
    """Fix Bug 3: Use out-neighbors for directed clustering coefficient.
    
    Using get_all_neighbors() (undirected: in+out) gives a larger neighborhood
    than the directed graph structure warrants. For directed clustering, only
    outgoing neighbors should define the neighborhood.
    """
    patch_file('/app/pipeline.py', [
        (
            '        # Collect neighborhood for each node: use all connections (in + out)\n'
            '        # for the neighborhood definition since influence flows both ways\n'
            '        neighborhoods = {}\n'
            '        for nid in sorted(graph.nodes.keys()):\n'
            '            neighborhoods[nid] = graph.get_all_neighbors(nid)',
            '        # Collect neighborhood for each node: use outgoing connections only\n'
            '        # for directed clustering coefficient computation\n'
            '        neighborhoods = {}\n'
            '        for nid in sorted(graph.nodes.keys()):\n'
            '            neighborhoods[nid] = graph.get_out_neighbors(nid)'
        ),
    ])


def main():
    """Apply all fixes and run the pipeline."""
    print("Applying Bug 1 fix (add shortest-path membership check)...")
    fix_bug1_betweenness_constraint()
    
    print("Applying Bug 2 fix (per-node normalization)...")
    fix_bug2_pagerank_normalization()
    
    print("Applying Bug 3 fix (out-neighbors for directed clustering)...")
    fix_bug3_clustering_neighborhood()
    
    print("All patches applied. Running pipeline...")
    result = subprocess.run(
        ['python3', '/app/pipeline.py'],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()
