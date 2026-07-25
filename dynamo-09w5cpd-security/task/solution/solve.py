#!/usr/bin/env python3
"""Oracle: fixes 3 bugs in the SAUTH verification system."""

# Fix 1: crypto.py — timestamp should be BE not LE
with open("/app/crypto.py") as f:
    code = f.read()
code = code.replace("struct.pack('<I', timestamp)", "struct.pack('>I', timestamp)")
with open("/app/crypto.py", "w") as f:
    f.write(code)

# Fix 2: verifier.py — handle legacy flag (bit 0x80) with truncated MAC
with open("/app/verifier.py") as f:
    code = f.read()
code = code.replace(
    '    if hmac_mod.compare_digest(expected, pkt["mac"]):\n'
    '        return True, "valid"\n\n'
    '    return False, "mac_mismatch"',
    '    if pkt["flags"] & 0x80:\n'
    '        if hmac_mod.compare_digest(expected[:8], pkt["mac"][:8]):\n'
    '            return True, "valid"\n'
    '    else:\n'
    '        if hmac_mod.compare_digest(expected, pkt["mac"]):\n'
    '            return True, "valid"\n\n'
    '    return False, "mac_mismatch"'
)
with open("/app/verifier.py", "w") as f:
    f.write(code)

# Fix 3: main.py — sort by seq not timestamp for replay detection
with open("/app/main.py") as f:
    code = f.read()
code = code.replace(
    '    valid_packets.sort(key=lambda x: x[1]["timestamp"])',
    '    valid_packets.sort(key=lambda x: x[1]["seq"])'
)
with open("/app/main.py", "w") as f:
    f.write(code)

# Run the fixed system on the input
exec(compile(open("/app/main.py").read(), "/app/main.py", "exec"))
