"""
Solution for the data validation pipeline.

Patches three cross-module data-flow bugs in pipeline.py:
1. Threshold computation uses all records instead of valid records only
2. Conditional rules receive pre-coercion values instead of coerced values
3. Referential integrity uses wrong column for reference value lookup
"""

import subprocess
import sys


def patch_pipeline():
    """Apply all three bug fixes to pipeline.py via string replacement."""
    pipeline_path = "/app/pipeline.py"

    with open(pipeline_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Fix 1: Compute threshold_stats from valid_records, not all records
    content = content.replace(
        "    # Compute quality thresholds from full dataset for population-level baselines\n"
        "    threshold_stats = compute_threshold_stats(records, table_schema)",
        "    # Compute quality thresholds from validated records only\n"
        "    threshold_stats = compute_threshold_stats(valid_records, table_schema)"
    )

    # Fix 2: Pass coerced_records to conditional rules instead of valid_records
    content = content.replace(
        "    # Evaluate conditional rules against source values to preserve data lineage\n"
        "    conditional_violations = evaluate_conditional_rules_for_table(\n"
        "        valid_records, table_schema, valid_records\n"
        "    )",
        "    # Evaluate conditional rules against coerced values for proper type comparison\n"
        "    conditional_violations = evaluate_conditional_rules_for_table(\n"
        "        coerced_records, table_schema, coerced_records\n"
        "    )"
    )

    # Fix 3: Use ref_column for reference values, not the first column
    content = content.replace(
        "        # Use primary key values as reference set for foreign key validation\n"
        "        ref_table_schema = table_schemas.get(ref_table, {})\n"
        "        ref_columns = ref_table_schema.get(\"columns\", [])\n"
        "        primary_column = ref_columns[0][\"name\"] if ref_columns else ref_column\n"
        "\n"
        "        reference_values = set()\n"
        "        for record in ref_records:\n"
        "            if primary_column in record and record[primary_column] is not None:\n"
        "                reference_values.add(str(record[primary_column]))",
        "        # Use the declared reference column for foreign key validation\n"
        "        reference_values = set()\n"
        "        for record in ref_records:\n"
        "            if ref_column in record and record[ref_column] is not None:\n"
        "                reference_values.add(str(record[ref_column]))"
    )

    with open(pipeline_path, "w", encoding="utf-8") as f:
        f.write(content)


def run_pipeline():
    """Run the patched pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Pipeline error: {result.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    patch_pipeline()
    run_pipeline()
