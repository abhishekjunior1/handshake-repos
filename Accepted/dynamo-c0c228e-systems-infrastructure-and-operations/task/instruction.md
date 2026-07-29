A shell environment profile compiler at `/app/pipeline.py` processes layered dotenv-style configurations into a resolved environment state. It uses modules `/app/file_parser.py`, `/app/interpolation_engine.py`, `/app/quote_handler.py`, `/app/merge_resolver.py`, `/app/export_filter.py`, and `/app/output_formatter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/env_profile.json` and writes `/app/output.json`.

The pipeline produces correct output on the current configuration but has bugs that cause incorrect results on other configurations. Find and fix the bugs so the pipeline handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure. In particular, preserve the case-sensitive prefix matching for export filtering (POSIX environment variable names are case-sensitive) and the priority-based layer merging semantics in merge_resolver (higher priority layers override lower ones for the same variable name; when layers share equal priority, later-declared layers take precedence).

The fixed pipeline will be tested on a different configuration than the one at `/app/env_profile.json`.

Output: `/app/output.json` — a JSON object with version, format, environment (sorted dict of variable_name: resolved_value for exported variables), and metadata containing source_attribution (variable_name: layer_name), layers (list of layer summaries with name/priority/variable_count), total_variables count, and settings.
