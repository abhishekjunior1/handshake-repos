A binary archive parser at `/app/main.py` extracts records from `.bvault` files. It uses `/app/parser.py`, `/app/checksum.py`, and `/app/encoding.py`.

Run it with `python3 /app/main.py`. It reads `/app/sample.bvault` and writes `/app/output.json`.

The parser works correctly on most records in the sample but fails on one. It also has bugs that cause incorrect results on other valid archives. Find and fix the bugs so it handles all valid BinVault v2 archives.

Do not rewrite from scratch — preserve the existing module structure. The fixed parser will be tested on a different archive than `/app/sample.bvault`.

Output: `/app/output.json` — JSON with keys "archive", "records", and "summary". All records must parse without errors and all integrity checks must pass.
