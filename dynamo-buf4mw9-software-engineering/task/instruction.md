A PLC data historian migration pipeline at `/app/pipeline.py` converts legacy binary archive data to structured JSON time-series output. It uses modules `/app/archive_reader.py`, `/app/quality_decoder.py`, `/app/timestamp_engine.py`, `/app/calibration.py`, and `/app/output_writer.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/manifest.json` and writes `/app/output.json`.

The manifest contains tag configurations (type, calibration parameters, scan rate) and hex-encoded binary archive blocks. Each archive block holds timestamped raw sensor samples for one tag (process variable). The pipeline processes each tag through quality decoding, calibration, gap detection/interpolation, and timestamp conversion.

The pipeline produces correct output on the current manifest but has bugs that cause incorrect results on other manifests — particularly those with discrete (boolean/state) tags, faster scan rates, or non-trivial gap patterns. Find and fix the bugs so the pipeline handles all valid manifests correctly.

The archive format stores samples in block order which may be non-monotonic across scan groups. The quality decoder uses reverse-chronological propagation for historian backfill batches where later annotations retroactively affect earlier samples. These are intentional design choices matching the source system's semantics — preserve them.

Do not rewrite from scratch — preserve the existing module structure and the historian-specific processing conventions (quality propagation direction, timestamp ordering preservation).

Output: `/app/output.json` — a JSON object with `metadata` (containing `source_format`, `migration_version`, `tag_count`, `total_samples`) and `tags` array where each tag has `tag_id`, `tag_type`, `sample_count`, `calibration_applied`, and `samples` array. Each sample has `timestamp_iso`, `value`, `quality_severity`, and `interpolated` fields.
