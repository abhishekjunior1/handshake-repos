"""Build scheduling and execution plan generation."""


def create_build_plan(ordered_derivations: list, cache_results: dict) -> dict:
    """Generate a build plan separating cached substitutes from required builds."""
    to_build = []
    to_substitute = []
    for drv in ordered_derivations:
        name = drv['name']
        cache_entry = cache_results.get(name, {})
        if cache_entry.get('hit', False):
            to_substitute.append({
                'name': name,
                'store_path': cache_entry['store_path'],
                'action': 'substitute',
            })
        else:
            to_build.append({
                'name': name,
                'store_path': cache_entry.get('store_path', ''),
                'action': 'build',
                'builder': drv['builder'],
            })
    return {
        'to_build': to_build,
        'to_substitute': to_substitute,
        'total_builds': len(to_build),
        'total_substitutes': len(to_substitute),
    }


def estimate_build_time(build_plan: dict) -> dict:
    """Estimate wall-clock build time based on plan complexity."""
    build_count = build_plan['total_builds']
    substitute_count = build_plan['total_substitutes']
    return {
        'estimated_build_seconds': build_count * 30,
        'estimated_substitute_seconds': substitute_count * 5,
        'estimated_total_seconds': build_count * 30 + substitute_count * 5,
    }


def get_build_order(build_plan: dict) -> list:
    """Return flat ordered list of all actions in execution sequence."""
    actions = []
    for item in build_plan['to_substitute']:
        actions.append(item)
    for item in build_plan['to_build']:
        actions.append(item)
    return actions
