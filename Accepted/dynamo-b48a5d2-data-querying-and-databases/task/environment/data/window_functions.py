"""Window functions module.

Implements analytical window functions over partitioned and ordered data.
Supports RUNNING_TOTAL (cumulative sum) and RANK functions.
Frame semantics default to RANGE per SQL standard when not specified.
"""

from typing import Any


def execute_window_function(rows: list[dict], spec: dict) -> list[dict]:
    """Execute a window function over the input rows.

    Args:
        rows: Input rows to process
        spec: Window specification with:
            - function: window function name (RUNNING_TOTAL, RANK)
            - partition_by: column(s) to partition by (optional)
            - order_by: column to order by within each partition
            - value_column: column to aggregate (for RUNNING_TOTAL)
            - alias: output column name
            - frame_mode: 'rows' or 'range' (defaults to range per SQL standard)

    Returns:
        Input rows augmented with the computed window column.
    """
    function = spec["function"].upper()
    partition_by = spec.get("partition_by")
    order_by = spec["order_by"]
    alias = spec.get("alias", f"{function.lower()}_result")

    partitions = _build_partitions(rows, partition_by)
    result_rows = []

    for partition in partitions:
        sorted_partition = sorted(partition, key=lambda r: r[order_by])

        if function == "RUNNING_TOTAL":
            computed = _compute_running_total(sorted_partition, spec)
        elif function == "RANK":
            computed = _compute_rank(sorted_partition, order_by)
        else:
            raise ValueError(f"Unknown window function: {function}")

        for row, value in zip(sorted_partition, computed):
            augmented = dict(row)
            augmented[alias] = value
            result_rows.append(augmented)

    return result_rows


def _build_partitions(rows: list[dict], partition_by: str | list | None) -> list[list[dict]]:
    """Split rows into partitions based on partition_by column(s)."""
    if not partition_by:
        return [list(rows)]

    if isinstance(partition_by, str):
        partition_by = [partition_by]

    partition_map: dict[tuple, list[dict]] = {}
    for row in rows:
        key = tuple(row[col] for col in partition_by)
        if key not in partition_map:
            partition_map[key] = []
        partition_map[key].append(row)

    return list(partition_map.values())


def _compute_running_total(sorted_rows: list[dict], spec: dict) -> list[float]:
    """Compute cumulative sum over ordered rows.

    Uses frame semantics to determine which rows contribute to each
    position's total. RANGE mode includes all peers (rows with the same
    ORDER BY value), while ROWS mode processes strictly row-by-row.
    """
    value_column = spec["value_column"]
    order_by = spec["order_by"]

    # SQL standard default frame
    frame_mode = spec.get("frame_mode", "range")

    values = [row[value_column] for row in sorted_rows]
    order_values = [row[order_by] for row in sorted_rows]

    if frame_mode == "rows":
        return _running_total_rows(values)
    else:
        return _running_total_range(values, order_values)


def _running_total_rows(values: list[float]) -> list[float]:
    """Row-by-row cumulative sum. Each row adds exactly one value."""
    totals = []
    running = 0
    for val in values:
        running += val
        totals.append(running)
    return totals


def _running_total_range(values: list[float], order_values: list[Any]) -> list[float]:
    """Range-based cumulative sum. All peers share the same running total.

    Peers are rows with identical ORDER BY values. The running total at any
    position includes all values from rows with ORDER BY value <= current.
    When peers exist, all peer positions get the same cumulative value.
    """
    n = len(values)
    totals = [0.0] * n
    cumulative = 0
    i = 0

    while i < n:
        j = i
        while j < n and order_values[j] == order_values[i]:
            j += 1

        peer_sum = sum(values[i:j])
        cumulative += peer_sum

        for k in range(i, j):
            totals[k] = cumulative

        i = j

    return totals


def _compute_rank(sorted_rows: list[dict], order_by: str) -> list[int]:
    """Compute RANK window function.

    Rows with the same ORDER BY value get the same rank.
    Next rank after tied rows skips positions.
    """
    n = len(sorted_rows)
    ranks = [0] * n

    current_rank = 1
    i = 0

    while i < n:
        j = i
        while j < n and sorted_rows[j][order_by] == sorted_rows[i][order_by]:
            j += 1

        for k in range(i, j):
            ranks[k] = current_rank

        current_rank = j + 1
        i = j

    return ranks
