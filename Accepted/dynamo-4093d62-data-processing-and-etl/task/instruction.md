A data validation pipeline at `/app/pipeline.py` validates datasets against schema definitions. It loads data and schema files, validates record types and nullability, coerces values to declared types, checks range and pattern constraints, evaluates conditional validation rules, performs referential integrity checks across tables, and computes per-column quality scores.

The pipeline uses modules `/app/data_loader.py`, `/app/schema_validator.py`, `/app/type_coercer.py`, `/app/constraint_checker.py`, `/app/integrity_checker.py`, `/app/quality_scorer.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/dataset.json` and `/app/schema.json` and writes `/app/output.json`.

The pipeline produces correct output on the current dataset but has bugs that cause incorrect results on other inputs. Find and fix the bugs so the pipeline handles all valid inputs correctly, including multi-table datasets with numeric columns, conditional validation rules, and cross-table foreign key relationships.

Do not rewrite from scratch — preserve the existing module structure and validation approach. The fixed pipeline will be tested on a different dataset than the one at `/app/dataset.json`.

Output: `/app/output.json` — a JSON object with structure:
```
{
  "dataset": "<name>",
  "tables": {
    "<table_name>": {
      "total_records": <int>,
      "valid_records": <int>,
      "invalid_records": <int>,
      "column_scores": {"<col>": <float 0.0-1.0>, ...},
      "overall_score": <float 0.0-1.0>,
      "violations": [{"record_index": <int>, "column": "<str>", "rule": "<str>", "value": "<str>", "message": "<str>"}, ...],
      "conditional_violations": [...],
      "integrity_violations": [...]
    }
  }
}
```
