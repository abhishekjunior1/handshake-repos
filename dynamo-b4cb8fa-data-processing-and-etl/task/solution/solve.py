"""
Oracle solution for tabular transformation pipeline.

Patches three bugs in the pipeline:
1. derived_columns uses stale snapshot instead of current working_data
2. pivot uses first-value semantics instead of sum for duplicate keys
3. join uses raw right table without coercing types to match left table
"""

import subprocess
import sys


def patch_pipeline():
    """Apply string replacement patches to fix all three bugs."""
    pipeline_path = "/app/pipeline.py"

    with open(pipeline_path, 'r') as f:
        content = f.read()

    # Bug 1 fix: Use working_data instead of primary_snapshot for derived columns
    content = content.replace(
        "        elif op_type == 'derived_columns':\n"
        "            derived_defs = op.get('columns', [])\n"
        "            # Use primary table snapshot for derived column computation\n"
        "            working_data = aggregator.compute_derived(primary_snapshot, derived_defs)",
        "        elif op_type == 'derived_columns':\n"
        "            derived_defs = op.get('columns', [])\n"
        "            # Use current working data for derived column computation\n"
        "            working_data = aggregator.compute_derived(working_data, derived_defs)"
    )

    # Bug 3 fix: Coerce right table join key types to match left table
    content = content.replace(
        "        elif op_type == 'join':\n"
        "            right_table_name = op['right_table']\n"
        "            right_rows = tables[right_table_name]\n"
        "            left_key = op['left_key']\n"
        "            right_key = op['right_key']\n"
        "            how = op.get('how', 'left')\n"
        "            working_data = join_ops.merge_tables(\n"
        "                working_data, right_rows, left_key, right_key, how)",
        "        elif op_type == 'join':\n"
        "            right_table_name = op['right_table']\n"
        "            right_rows = list(tables[right_table_name])\n"
        "            left_key = op['left_key']\n"
        "            right_key = op['right_key']\n"
        "            how = op.get('how', 'left')\n"
        "            # Coerce right table key types to match left table\n"
        "            if working_data and left_key in working_data[0]:\n"
        "                left_val = working_data[0][left_key]\n"
        "                if isinstance(left_val, int):\n"
        "                    right_rows = column_mapper.apply_type_coercion(right_rows, {right_key: 'int'})\n"
        "                elif isinstance(left_val, float):\n"
        "                    right_rows = column_mapper.apply_type_coercion(right_rows, {right_key: 'float'})\n"
        "            working_data = join_ops.merge_tables(\n"
        "                working_data, right_rows, left_key, right_key, how)"
    )

    with open(pipeline_path, 'w') as f:
        f.write(content)

    # Bug 2 fix: Change pivot from first-value to sum semantics
    pivot_path = "/app/pivot_ops.py"
    with open(pivot_path, 'r') as f:
        pivot_content = f.read()

    pivot_content = pivot_content.replace(
        "        # Use first value encountered for each (index, pivot) pair\n"
        "        if pval not in groups[idx]:\n"
        "            groups[idx][pval] = vval",
        "        # Sum values for each (index, pivot) pair\n"
        "        if pval not in groups[idx]:\n"
        "            groups[idx][pval] = 0\n"
        "        if vval is not None:\n"
        "            groups[idx][pval] += float(vval) if not isinstance(vval, (int, float)) else vval"
    )

    with open(pivot_path, 'w') as f:
        f.write(pivot_content)

    print("All patches applied successfully.")


def run_pipeline():
    """Run the patched pipeline."""
    result = subprocess.run(
        ["python3", "/app/pipeline.py", "/app/transform_config.json", "/app/output.json"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    patch_pipeline()
    exit_code = run_pipeline()
    sys.exit(exit_code)
