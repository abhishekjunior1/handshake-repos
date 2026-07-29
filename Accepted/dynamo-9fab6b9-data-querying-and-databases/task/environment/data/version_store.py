"""
Versioned row storage for MVCC.

Manages multiple versions of each row, where each version is tagged
with the transaction that created it (xmin) and optionally the
transaction that deleted/superseded it (xmax).
"""


def load_version_store(store_config):
    """Load the version store from configuration.

    The version store maps row IDs to lists of versions.
    Each version has: xmin, xmax (0 if current), cid, data.

    Args:
        store_config: Dictionary mapping row_id to version lists

    Returns:
        Dictionary of {row_id: [versions]}
    """
    return dict(store_config)


def get_row_versions(version_store, row_id):
    """Get all versions for a specific row.

    Args:
        version_store: Full version store
        row_id: Row identifier

    Returns:
        List of version dictionaries
    """
    return version_store.get(row_id, [])


def get_latest_version(versions):
    """Get the most recent version (highest xmin, xmax=0).

    Args:
        versions: List of version dicts

    Returns:
        Latest version dict or None
    """
    current = [v for v in versions if v.get('xmax', 0) == 0]
    if current:
        return max(current, key=lambda v: v['xmin'])
    return max(versions, key=lambda v: v['xmin']) if versions else None


def count_live_versions(version_store):
    """Count versions that haven't been deleted (xmax=0).

    Args:
        version_store: Full version store

    Returns:
        Count of live versions
    """
    count = 0
    for row_id, versions in version_store.items():
        for v in versions:
            if v.get('xmax', 0) == 0:
                count += 1
    return count
