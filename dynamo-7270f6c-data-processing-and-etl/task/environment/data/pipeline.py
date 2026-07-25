import sys
from config import load_json, save_json, SOURCE_PATH, OUTPUT_PATH
from schema import validate_and_normalize
from transformer import transform_records
from merger import deduplicate_records, compute_change_log, compute_merge_statistics
from aggregator import aggregate_records


def run_pipeline(source_path=None):
    input_path = source_path or SOURCE_PATH
    raw_records = load_json(input_path)

    valid_records, rejected = validate_and_normalize(raw_records)

    transformed = transform_records(valid_records)

    aggregation = aggregate_records(transformed)

    merged = deduplicate_records(transformed)

    merge_stats = compute_merge_statistics(len(transformed), len(merged))
    change_log = compute_change_log([], merged)

    output = {
        "records": merged,
        "aggregation": aggregation,
        "metadata": {
            "total_input": len(raw_records),
            "valid": len(valid_records),
            "rejected": len(rejected),
            "merged_count": len(merged),
            "duplicates_removed": merge_stats["duplicates_removed"],
            "dedup_ratio": merge_stats["dedup_ratio"],
            "changes": len(change_log),
        },
    }

    save_json(output, OUTPUT_PATH)
    print(f"Pipeline complete. Processed {len(raw_records)} records.")
    print(f"Valid: {len(valid_records)}, Rejected: {len(rejected)}")
    print(f"Merged: {len(merged)}, Windows: {aggregation['total_windows']}")
    return output


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(source)
