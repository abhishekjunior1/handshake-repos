"""Window functions module for the analytical query engine.

Implements SQL-standard window functions: ROW_NUMBER, RANK, DENSE_RANK,
running totals, and running averages over partitioned and ordered data.

Window frame semantics follow the SQL standard: when no explicit frame
is specified, the default is RANGE UNBOUNDED PRECEDING which includes
all peer rows (rows with the same ORDER BY value as the current row).
"""

from typing import Any
from functools import cmp_to_key


def apply_window_functions(
    rows: list[dict],
    window_specs: list[dict],
) -> list[dict]:
    """Apply window function specifications to rows.

    Each window spec defines: function, partition_by, order_by, alias,
    and optional frame_mode ('rows' or 'range'). When frame_mode is not
    specified, defaults to 'range' per SQL standard.
    """
    result_rows = [dict(row) for row in rows]

    for spec in window_specs:
        result_rows = _apply_single_window(result_rows, spec)

    return result_rows


def _apply_single_window(rows: list[dict], spec: dict) -> list[dict]:
    """Apply a single window function to all rows."""
    function = spec["function"].upper()
    partition_by = spec.get("partition_by", [])
    order_by = spec.get("order_by", [])
    alias = spec["alias"]
    column = spec.get("column")
    # SQL standard: default frame is RANGE when not explicitly specified
    frame_mode = spec.get("frame_mode", "range")

    partitions = _build_partitions(rows, partition_by)

    for partition_rows in partitions.values():
        sorted_partition = _sort_rows(partition_rows, order_by)

        if function == "ROW_NUMBER":
            _assign_row_number(sorted_partition, alias)
        elif function == "RANK":
            _assign_rank(sorted_partition, order_by, alias)
        elif function == "DENSE_RANK":
            _assign_dense_rank(sorted_partition, order_by, alias)
        elif function == "RUNNING_TOTAL":
            _assign_running_total(sorted_partition, column, alias,
                                  order_by, frame_mode)
        elif function == "RUNNING_AVG":
            _assign_running_avg(sorted_partition, column, alias,
                                order_by, frame_mode)
        elif function == "LAG":
            offset = spec.get("offset", 1)
            _assign_lag(sorted_partition, column, alias, offset)
        elif function == "LEAD":
            offset = spec.get("offset", 1)
            _assign_lead(sorted_partition, column, alias, offset)
        else:
            raise ValueError(f"Unknown window function: {function}")

    return rows


def _build_partitions(
    rows: list[dict], partition_by: list[str]
) -> dict[tuple, list[dict]]:
    """Partition rows by the specified columns."""
    if not partition_by:
        return {(): rows}

    partitions = {}
    for row in rows:
        key = tuple(row.get(col) for col in partition_by)
        if key not in partitions:
            partitions[key] = []
        partitions[key].append(row)
    return partitions


def _sort_rows(rows: list[dict], order_by: list[dict]) -> list[dict]:
    """Sort rows by order_by specification.

    NULL values are sorted LAST regardless of direction (SQL NULLS LAST).
    """
    if not order_by:
        return rows

    def compare_rows(a, b):
        for spec in order_by:
            col = spec["column"]
            desc = spec.get("direction", "asc").lower() == "desc"
            val_a = a.get(col)
            val_b = b.get(col)

            if val_a is None and val_b is None:
                continue
            if val_a is None:
                return 1
            if val_b is None:
                return -1

            if val_a < val_b:
                return 1 if desc else -1
            elif val_a > val_b:
                return -1 if desc else 1

        return 0

    rows.sort(key=cmp_to_key(compare_rows))
    return rows


def _get_order_key(row: dict, order_by: list[dict]) -> tuple:
    """Get the ordering key tuple for a row."""
    return tuple(row.get(spec["column"]) for spec in order_by)


def _assign_row_number(rows: list[dict], alias: str) -> None:
    """Assign sequential row numbers starting from 1."""
    for i, row in enumerate(rows):
        row[alias] = i + 1


def _assign_rank(rows: list[dict], order_by: list[dict], alias: str) -> None:
    """Assign rank with gaps for ties."""
    if not rows:
        return

    rows[0][alias] = 1
    for i in range(1, len(rows)):
        if _get_order_key(rows[i], order_by) == _get_order_key(rows[i - 1], order_by):
            rows[i][alias] = rows[i - 1][alias]
        else:
            rows[i][alias] = i + 1


def _assign_dense_rank(rows: list[dict], order_by: list[dict], alias: str) -> None:
    """Assign dense rank (no gaps between ranks)."""
    if not rows:
        return

    rows[0][alias] = 1
    for i in range(1, len(rows)):
        if _get_order_key(rows[i], order_by) == _get_order_key(rows[i - 1], order_by):
            rows[i][alias] = rows[i - 1][alias]
        else:
            rows[i][alias] = rows[i - 1][alias] + 1


def _assign_running_total(rows: list[dict], column: str, alias: str,
                          order_by: list[dict], frame_mode: str) -> None:
    """Compute running total over the specified column.

    With frame_mode='rows': cumulative sum up to and including current row.
    With frame_mode='range': cumulative sum including all peer rows
    (rows with the same ORDER BY value as current row).
    """
    if frame_mode == "rows":
        running = 0
        for row in rows:
            val = row.get(column)
            if val is not None:
                running += val
            row[alias] = running
    else:
        # RANGE mode: include all peers (rows with same order key)
        # First compute prefix sums, then for each row find the last peer
        # and assign that peer's prefix sum
        prefix_sums = []
        running = 0
        for row in rows:
            val = row.get(column)
            if val is not None:
                running += val
            prefix_sums.append(running)

        # For RANGE: all rows with the same order key get the same running total
        # (the total including all peers)
        n = len(rows)
        i = 0
        while i < n:
            # Find the end of the peer group
            j = i + 1
            while j < n and _get_order_key(rows[j], order_by) == _get_order_key(rows[i], order_by):
                j += 1
            # All peers get the prefix sum at the last peer position
            peer_total = prefix_sums[j - 1]
            for k in range(i, j):
                rows[k][alias] = peer_total
            i = j


def _assign_running_avg(rows: list[dict], column: str, alias: str,
                        order_by: list[dict], frame_mode: str) -> None:
    """Compute running average over the specified column."""
    if frame_mode == "rows":
        running_sum = 0
        count = 0
        for row in rows:
            val = row.get(column)
            if val is not None:
                running_sum += val
                count += 1
            row[alias] = round(running_sum / count, 6) if count > 0 else None
    else:
        # RANGE mode: include all peers
        prefix_sums = []
        prefix_counts = []
        running_sum = 0
        count = 0
        for row in rows:
            val = row.get(column)
            if val is not None:
                running_sum += val
                count += 1
            prefix_sums.append(running_sum)
            prefix_counts.append(count)

        n = len(rows)
        i = 0
        while i < n:
            j = i + 1
            while j < n and _get_order_key(rows[j], order_by) == _get_order_key(rows[i], order_by):
                j += 1
            peer_sum = prefix_sums[j - 1]
            peer_count = prefix_counts[j - 1]
            peer_avg = round(peer_sum / peer_count, 6) if peer_count > 0 else None
            for k in range(i, j):
                rows[k][alias] = peer_avg
            i = j


def _assign_lag(rows: list[dict], column: str, alias: str, offset: int) -> None:
    """Assign LAG value (value from N rows before in partition order)."""
    for i, row in enumerate(rows):
        if i >= offset:
            row[alias] = rows[i - offset].get(column)
        else:
            row[alias] = None


def _assign_lead(rows: list[dict], column: str, alias: str, offset: int) -> None:
    """Assign LEAD value (value from N rows ahead in partition order)."""
    for i, row in enumerate(rows):
        if i + offset < len(rows):
            row[alias] = rows[i + offset].get(column)
        else:
            row[alias] = None
