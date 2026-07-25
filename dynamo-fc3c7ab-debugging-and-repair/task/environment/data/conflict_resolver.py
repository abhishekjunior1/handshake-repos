"""
Conflict Resolver Module
========================
Handles mutual exclusion groups for feature flags. When flags are in a
mutex group, only one flag in the group can be enabled for a given device.

Resolution strategy: Within a mutex group, flags are evaluated in the order
they are processed. The LAST flag that would be enabled wins (last-writer-wins).
This means processing order matters — the final enabled flag in processing
sequence becomes the sole enabled flag for that mutex group.

Priority field provides a tiebreaker hint but does not override the
last-writer-wins semantic when flags have equal priority.
"""

from typing import Dict, List


def resolve_conflicts(evaluations: dict, mutex_groups: list, flag_order: list) -> dict:
    """
    Resolve mutual exclusion conflicts in flag evaluations.

    For each mutex group, ensures only one flag is enabled per device.
    Uses last-writer-wins semantics based on the provided flag processing order.

    Args:
        evaluations: Current evaluation state {flag_name: {enabled, reason}}.
        mutex_groups: List of mutex group definitions.
        flag_order: Ordered list of flag names (processing order determines winners).

    Returns:
        Dictionary with:
        - 'evaluations': Updated evaluations with conflicts resolved.
        - 'resolutions': List of conflict resolution records.
        - 'groups_processed': Number of mutex groups that had active conflicts.
    """
    if not mutex_groups:
        return {
            "evaluations": evaluations,
            "resolutions": [],
            "groups_processed": 0,
        }

    resolutions = []
    groups_processed = 0

    for group in mutex_groups:
        group_name = group.get("name", "unnamed")
        group_flags = group.get("flags", [])
        group_priority = group.get("priority_order", [])

        if len(group_flags) < 2:
            continue

        # Find which flags in this group are currently enabled
        enabled_in_group = [
            f for f in group_flags
            if f in evaluations and evaluations[f]["enabled"]
        ]

        if len(enabled_in_group) <= 1:
            continue

        # Conflict detected — resolve using last-writer-wins based on processing order
        groups_processed += 1
        winner = _determine_winner(enabled_in_group, flag_order, group_priority)

        # Disable all but the winner
        for flag_name in enabled_in_group:
            if flag_name != winner:
                evaluations[flag_name]["enabled"] = False
                evaluations[flag_name]["reason"] = "conflict"
                resolutions.append({
                    "group": group_name,
                    "flag": flag_name,
                    "action": "disabled",
                    "winner": winner,
                    "reason": f"mutex_group:{group_name}:winner={winner}",
                })

    return {
        "evaluations": evaluations,
        "resolutions": resolutions,
        "groups_processed": groups_processed,
    }


def _determine_winner(enabled_flags: list, flag_order: list, priority_order: list) -> str:
    """
    Determine the winner in a mutex group conflict.

    Uses last-writer-wins: the flag that appears LAST in processing order wins.
    If priority_order is specified and flags have explicit priority positions,
    those take precedence.

    Args:
        enabled_flags: Flags in the group that are currently enabled.
        flag_order: Processing order of all flags.
        priority_order: Optional explicit priority ordering for this group.

    Returns:
        Name of the winning flag.
    """
    # If explicit priority order is defined for this group, use it
    if priority_order:
        for flag in priority_order:
            if flag in enabled_flags:
                return flag

    # Fall back to last-writer-wins based on processing order
    last_index = -1
    winner = enabled_flags[0]

    for flag_name in enabled_flags:
        try:
            idx = flag_order.index(flag_name)
            if idx > last_index:
                last_index = idx
                winner = flag_name
        except ValueError:
            continue

    return winner


def identify_mutex_conflicts(evaluations: dict, mutex_groups: list) -> List[dict]:
    """
    Identify potential mutex conflicts without resolving them.

    Useful for reporting and diagnostics.

    Args:
        evaluations: Current evaluation state.
        mutex_groups: List of mutex group definitions.

    Returns:
        List of conflict records identifying groups with multiple enabled flags.
    """
    conflicts = []

    for group in mutex_groups:
        group_name = group.get("name", "unnamed")
        group_flags = group.get("flags", [])

        enabled_in_group = [
            f for f in group_flags
            if f in evaluations and evaluations[f]["enabled"]
        ]

        if len(enabled_in_group) > 1:
            conflicts.append({
                "group": group_name,
                "enabled_flags": enabled_in_group,
                "conflict_count": len(enabled_in_group) - 1,
            })

    return conflicts
