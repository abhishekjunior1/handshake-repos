"""
Tabular data transformation pipeline orchestrator.

Executes transformation operations on input tables: column mapping,
joins, pivots, derived columns, and aggregations.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import data_loader
import column_mapper
import pivot_ops
import join_ops
import aggregator
import output_writer


def run_pipeline(config_path, output_path):
    """Execute the transformation pipeline.

    Processes all operations defined in the configuration, applying
    them to the working dataset in sequence.
    """
    config = data_loader.load_config(config_path)
    tables = data_loader.load_tables(config)
    operations = data_loader.get_operations(config)
    output_config = data_loader.get_output_config(config)

    source_table_names = list(tables.keys())
    transformations_applied = []

    # Start with the primary table
    primary_name = source_table_names[0]
    working_data = list(tables[primary_name])

    # Snapshot of primary table for derived column references
    primary_snapshot = list(tables[primary_name])

    for op in operations:
        op_type = op['type']

        if op_type == 'coerce_types':
            type_map = op.get('type_map', {})
            working_data = column_mapper.apply_type_coercion(working_data, type_map)
            transformations_applied.append('type_coercion')

        elif op_type == 'rename_columns':
            col_map = op.get('column_map', {})
            working_data = column_mapper.rename_columns(working_data, col_map)
            # Update snapshot column names to match
            primary_snapshot = column_mapper.rename_columns(primary_snapshot, col_map)
            transformations_applied.append('rename_columns')

        elif op_type == 'join':
            right_table_name = op['right_table']
            right_rows = tables[right_table_name]
            left_key = op['left_key']
            right_key = op['right_key']
            how = op.get('how', 'left')
            working_data = join_ops.merge_tables(
                working_data, right_rows, left_key, right_key, how)
            transformations_applied.append('join')

        elif op_type == 'pivot':
            index_col = op['index_col']
            pivot_col = op['pivot_col']
            value_col = op['value_col']
            working_data = pivot_ops.pivot_table(
                working_data, index_col, pivot_col, value_col)
            transformations_applied.append('pivot')

        elif op_type == 'derived_columns':
            derived_defs = op.get('columns', [])
            # Use primary table snapshot for derived column computation
            working_data = aggregator.compute_derived(primary_snapshot, derived_defs)
            transformations_applied.append('derived_columns')

        elif op_type == 'aggregate':
            group_by = op.get('group_by', [])
            aggs = op.get('aggregations', [])
            working_data = aggregator.aggregate_groups(
                working_data, group_by, aggs)
            transformations_applied.append('aggregate')

        elif op_type == 'select_columns':
            columns = op.get('columns', [])
            working_data = column_mapper.select_columns(working_data, columns)
            transformations_applied.append('select_columns')

    # Apply output formatting
    sort_by = output_config.get('sort_by')
    sort_order = output_config.get('sort_order', 'descending')
    if sort_by:
        working_data = output_writer.sort_rows(working_data, sort_by, sort_order)

    output_cols = output_config.get('columns')
    if output_cols:
        working_data = column_mapper.select_columns(working_data, output_cols)

    metadata = {
        'transformations': transformations_applied,
        'source_tables': source_table_names
    }

    output = output_writer.format_output(working_data, metadata)
    output_writer.write_output(output, output_path)

    print(f"Pipeline complete: {len(working_data)} rows, "
          f"{len(transformations_applied)} transformations applied")


if __name__ == '__main__':
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'transform_config.json')
    output_file = '/app/output.json'

    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    run_pipeline(config_file, output_file)
