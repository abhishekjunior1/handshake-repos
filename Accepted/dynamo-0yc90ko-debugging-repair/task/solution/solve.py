#!/usr/bin/env python3
"""Oracle: fixes 3 bugs in the event processing pipeline."""

# Fix 1: config.py — round() not int() for score computation
with open("/app/config.py") as f:
    code = f.read()
code = code.replace("return int(priority * impact) + weight", "return round(priority * impact) + weight")
with open("/app/config.py", "w") as f:
    f.write(code)

# Fix 2: aggregator.py — dedup by event_id not timestamp
with open("/app/aggregator.py") as f:
    code = f.read()
code = code.replace(
    '        dedup_key = ev["timestamp"]',
    '        dedup_key = ev["event_id"]'
)
with open("/app/aggregator.py", "w") as f:
    f.write(code)

# Fix 3: process.py — sort by event_id for deterministic processing
with open("/app/process.py") as f:
    code = f.read()
code = code.replace(
    '    parsed.sort(key=lambda x: x["timestamp"])',
    '    parsed.sort(key=lambda x: x["event_id"])'
)
with open("/app/process.py", "w") as f:
    f.write(code)

# Run fixed pipeline
exec(compile(open("/app/process.py").read(), "/app/process.py", "exec"))
