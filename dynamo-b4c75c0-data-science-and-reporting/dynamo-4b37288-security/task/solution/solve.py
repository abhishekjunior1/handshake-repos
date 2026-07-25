#!/usr/bin/env python3
"""Fix BinVault parser bugs."""
import sys


def main():
    # Fix 1: parser.py — types 0x04/0x05 use payload-only length
    with open('/app/parser.py') as f: c = f.read()
    c = c.replace(
        '    payload_size = rec_length - 6',
        '    payload_size = rec_length if rec_type in (0x04, 0x05) else rec_length - 6')
    with open('/app/parser.py', 'w') as f: f.write(c)

    # Fix 2: checksum.py — CRC on raw stored bytes, not decoded
    with open('/app/checksum.py') as f: c = f.read()
    c = c.replace(
        '    decoded = decode_data(data, encoding)\n'
        '    return (zlib.crc32(decoded) & 0xFFFFFFFF) == expected',
        '    return (zlib.crc32(data) & 0xFFFFFFFF) == expected')
    with open('/app/checksum.py', 'w') as f: f.write(c)

    # Run
    sys.path.insert(0, '/app')
    for m in list(sys.modules):
        if m in ('main','parser','checksum','encoding','records'):
            del sys.modules[m]
    from main import extract
    extract('/app/sample.bvault', '/app/output.json')


if __name__ == "__main__":
    main()
