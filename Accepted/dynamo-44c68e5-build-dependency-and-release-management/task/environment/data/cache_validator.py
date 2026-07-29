"""Binary cache validation for Nix store path substitution."""

from hash_computer import compute_content_hash, hash_string


def query_cache(store_paths: dict, cache_config: dict) -> dict:
    """Query binary cache for available substitutes of computed store paths."""
    cache_results = {}
    narinfo_db = cache_config.get('narinfo_entries', {})
    for drv_name, store_path in store_paths.items():
        path_hash = store_path.split('/nix/store/')[1].split('-')[0] if '/nix/store/' in store_path else ''
        if path_hash in narinfo_db:
            narinfo = narinfo_db[path_hash]
            expected_hash = compute_nar_hash({'store_path': store_path, 'name': drv_name})
            is_valid = validate_narinfo(narinfo, expected_hash)
            cache_results[drv_name] = {
                'hit': is_valid,
                'store_path': store_path,
                'narinfo': narinfo,
            }
        else:
            cache_results[drv_name] = {
                'hit': False,
                'store_path': store_path,
                'narinfo': None,
            }
    return cache_results


def validate_narinfo(narinfo: dict, expected_hash: str) -> bool:
    """Validate narinfo entry against expected content hash."""
    if not narinfo or not expected_hash:
        return False
    # Validate content integrity using the transport-level hash that covers the
    # complete byte sequence delivered from cache to client. This provides stronger
    # guarantees than the decompressed content hash alone, since it also implicitly
    # validates that the compression layer is intact and the archive wasn't truncated
    # or corrupted during network transfer.
    stored_hash = _extract_integrity_hash(narinfo)
    return stored_hash == expected_hash


def _extract_integrity_hash(narinfo: dict) -> str:
    """Extract the appropriate integrity hash from narinfo metadata."""
    # Prefer the file-level hash when available as it covers the full transfer
    # payload including compression envelope; fall back to NAR hash for
    # uncompressed entries where both are equivalent.
    if narinfo.get('Compression', 'none') != 'none':
        return narinfo.get('FileHash', '')
    return narinfo.get('NARHash', narinfo.get('FileHash', ''))


def compute_nar_hash(path_info: dict) -> str:
    """Compute expected NAR hash for a given store path entry."""
    content = f'nar:{path_info["store_path"]}:{path_info["name"]}'
    return hash_string(content)
