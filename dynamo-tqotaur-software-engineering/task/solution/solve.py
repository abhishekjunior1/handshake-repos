#!/usr/bin/env python3
"""Oracle: fix boolean printing and for-loop scoping bugs."""
import shutil, os

shutil.copy('/app/pebble.py', '/app/pebble')

with open('/app/pebble') as f:
    code = f.read()

# Fix 1: boolean printing (str(True) -> "true")
code = code.replace(
    "            self.out.append(str(v))",
    "            self.out.append(str(v).lower() if isinstance(v, bool) else str(v))"
)

# Fix 2: for-loop must create fresh scope per iteration
code = code.replace(
    "            ie = Env(env); ie.define(s[1], Cell(st))\n            for i in range(st, en):\n                ie.lookup(s[1]).val = i; self.xblock(s[4], ie)",
    "            for i in range(st, en):\n                ie = Env(env); ie.define(s[1], Cell(i)); self.xblock(s[4], ie)"
)

with open('/app/pebble', 'w') as f:
    f.write(code)

os.chmod('/app/pebble', 0o755)
