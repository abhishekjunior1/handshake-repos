#!/usr/bin/env python3
"""Oracle: fixes 3 bugs in the pipeline orchestrator."""
import subprocess

# Fix 1: dependencies.py — use insertion order instead of sorted()
with open("/app/dependencies.py") as f:
    code = f.read()
code = code.replace(
    '    queue = sorted([n for n, d in in_degree.items() if d == 0])',
    '    queue = [n for n in stages if in_degree[n] == 0]'
)
code = code.replace(
    '        queue.sort()',
    '        pass  # preserve insertion order'
)
with open("/app/dependencies.py", "w") as f:
    f.write(code)

# Fix 2: state.py — get_latest_state should return last SUCCESSFUL snapshot
with open("/app/state.py") as f:
    code = f.read()
code = code.replace(
    '        # Return the most recent snapshot\n'
    '        return self._snapshots[stage_name][-1][0]',
    '        # Return the most recent successful snapshot\n'
    '        for state, success in reversed(self._snapshots[stage_name]):\n'
    '            if success:\n'
    '                return state\n'
    '        return {}'
)
with open("/app/state.py", "w") as f:
    f.write(code)

# Fix 3: executor.py — only record success AFTER validation passes
with open("/app/executor.py") as f:
    code = f.read()
code = code.replace(
    '            # Record as successful snapshot immediately\n'
    '            state_store.record_snapshot(name, output, True)\n'
    '\n'
    '            # Validate if validator exists\n'
    '            if validator:\n'
    '                is_valid = validator(output)\n'
    '                if not is_valid:\n'
    '                    # Mark this snapshot as actually failed\n'
    '                    state_store.record_snapshot(name, output, False)',
    '            # Validate if validator exists\n'
    '            if validator:\n'
    '                is_valid = validator(output)\n'
    '                if not is_valid:\n'
    '                    state_store.record_snapshot(name, output, False)'
)
code = code.replace(
    '            self._status[name] = "completed"\n'
    '            return "completed", output',
    '            # Record successful snapshot after validation\n'
    '            state_store.record_snapshot(name, output, True)\n'
    '            self._status[name] = "completed"\n'
    '            return "completed", output'
)
with open("/app/executor.py", "w") as f:
    f.write(code)

# Run the fixed pipeline
subprocess.run(["python3", "/app/pipeline.py"], check=True)
