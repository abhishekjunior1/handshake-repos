#!/usr/bin/env python3
"""Generate BinVault archives."""
import struct, json, zlib, base64, os

TIMESTAMP = 1736942400000


def crc32(d): return zlib.crc32(d) & 0xFFFFFFFF


def header(count):
    body = struct.pack('>4sHHIQ', b'BVLT', 2, 0x04, count, TIMESTAMP)
    return body + struct.pack('>I', crc32(body))


def metadata(k, v):
    kb, vb = k.encode(), v.encode()
    p = struct.pack('>H', len(kb)) + kb + struct.pack('>H', len(vb)) + vb
    return struct.pack('>BBI', 0x01, 0x00, 6 + len(p)) + p


def blob(bid, content, enc=0):
    if enc == 0: stored = content
    elif enc == 1: stored = base64.b64encode(content)
    elif enc == 2: stored = content.hex().encode()
    c = crc32(stored)  # CRC of STORED bytes (raw form in archive)
    p = struct.pack('>IBI', bid, enc, len(stored)) + stored + struct.pack('>I', c)
    return struct.pack('>BBI', 0x02, 0x00, 6 + len(p)) + p


def index(entries):
    p = struct.pack('>H', len(entries))
    for r, o in entries: p += struct.pack('>II', r, o)
    return struct.pack('>BBI', 0x03, 0x00, 6 + len(p)) + p


def delta(base, ops):
    p = struct.pack('>IH', base, len(ops))
    for ot, oo, ol, od in ops:
        p += struct.pack('>BIH', ot, oo, ol)
        if ot in (0, 2): p += od
    # Length = payload only (NOT including header)
    return struct.pack('>BBI', 0x04, 0x00, len(p)) + p


def xref(entries):
    p = struct.pack('>H', len(entries))
    for s, d, r, l in entries:
        lb = l.encode()
        p += struct.pack('>IIB', s, d, r) + struct.pack('>B', len(lb)) + lb
    # Length = payload only (NOT including header)
    return struct.pack('>BBI', 0x05, 0x00, len(p)) + p


def gen_sample():
    """Visible: types in ascending order (1,1,1,2,2,3,4).
    Sort by type == sequential order (masked).
    All BLOBs raw (checksum masked). DELTA at end (observable error)."""
    recs = [
        metadata("format", "BinVault v2"),
        metadata("creator", "archiver-1.0"),
        metadata("desc", "config backup"),
        blob(1, b"Primary config data block for system init.", enc=0),
        blob(2, b"Fallback recovery parameters for failover.", enc=0),
        index([(1, 78), (2, 140)]),
        delta(1, [(0, 0, 4, b"INIT"), (1, 20, 8, b"")]),
    ]
    return header(len(recs)) + b''.join(recs)


def gen_test():
    """Hidden: types INTERLEAVED (sort reorders != sequential).
    Has base64/hex BLOBs (checksum triggers). DELTA/XREF mid-stream."""
    recs = [
        metadata("format", "BinVault v2"),          # idx 0, type 1
        blob(100, b"Raw baseline payload.", enc=0), # idx 1, type 2
        delta(100, [(0, 0, 6, b"PREFIX"),           # idx 2, type 4
                    (2, 10, 3, b"NEW")]),
        metadata("suite", "test-001"),              # idx 3, type 1
        blob(101, b"Base64 encoded content for verification.", enc=1),  # idx 4, type 2
        xref([(100, 101, 0, "parent"),              # idx 5, type 5
              (101, 100, 1, "child")]),
        index([(100, 24), (101, 80)]),              # idx 6, type 3
        blob(102, b"Hex encoded test data.", enc=2),# idx 7, type 2
        delta(101, [(1, 0, 5, b""),                 # idx 8, type 4
                    (0, 20, 4, b"TAIL")]),
        xref([(100, 102, 2, "linked"),              # idx 9, type 5
              (102, 101, 3, "alias")]),
        index([(100, 24), (101, 80), (102, 200)]),  # idx 10, type 3
        metadata("checksum", "crc32"),              # idx 11, type 1
    ]
    return header(len(recs)) + b''.join(recs)


def parse_correct(data):
    """Parse with correct logic."""
    _, ver, flags, count, ts, _ = struct.unpack('>4sHHIQI', data[:24])
    records = []
    off = 24
    for i in range(count):
        rt = data[off]
        rf = data[off+1] ^ 0x00
        rl = struct.unpack('>I', data[off+2:off+6])[0]
        # Correct: types 1-3 total, types 4-5 payload-only
        ps = rl - 6 if rt in (1, 2, 3) else rl
        p = data[off+6:off+6+ps]
        off += 6 + ps
        records.append(_decode(rt, rf, p, i))

    # Correct output: sort by type code (this IS the intended output order)
    records.sort(key=lambda r: r.get("_sort", 0))
    for r in records: r.pop("_sort", None)

    types = {}
    for r in records:
        t = r.get("type", "?")
        types[t] = types.get(t, 0) + 1

    return {
        "archive": {"file": "sample.bvault", "size": len(data),
                    "version": ver, "flags": flags, "records": count, "timestamp": ts},
        "records": records,
        "summary": {"total": len(records), "types": types, "errors": 0}
    }


def _decode(rt, rf, p, idx):
    result = {"record_index": idx, "flags": rf, "_sort": rt}
    if rt == 1:
        kl = struct.unpack_from('>H', p, 0)[0]
        k = p[2:2+kl].decode()
        vl = struct.unpack_from('>H', p, 2+kl)[0]
        v = p[4+kl:4+kl+vl].decode()
        result.update(type="METADATA", key=k, value=v)
    elif rt == 2:
        bid = struct.unpack_from('>I', p, 0)[0]
        enc = p[4]
        dl = struct.unpack_from('>I', p, 5)[0]
        raw = p[9:9+dl]
        sc = struct.unpack_from('>I', p, 9+dl)[0]
        # Correct: CRC on stored bytes
        ok = (crc32(raw) == sc)
        if enc == 0: dec = raw
        elif enc == 1: dec = base64.b64decode(raw)
        elif enc == 2: dec = bytes.fromhex(raw.decode())
        result.update(type="BLOB", blob_id=bid, encoding=enc,
                     data_length=len(dec), preview=dec[:64].hex(),
                     checksum_valid=ok, checksum_stored=sc)
    elif rt == 3:
        n = struct.unpack_from('>H', p, 0)[0]
        entries = []; o = 2
        for _ in range(n):
            entries.append({"ref": struct.unpack_from('>I', p, o)[0],
                          "offset": struct.unpack_from('>I', p, o+4)[0]}); o += 8
        result.update(type="INDEX", count=n, entries=entries)
    elif rt == 4:
        base = struct.unpack_from('>I', p, 0)[0]
        n = struct.unpack_from('>H', p, 4)[0]
        ops = []; o = 6
        for _ in range(n):
            ot = p[o]; o += 1
            oo = struct.unpack_from('>I', p, o)[0]; o += 4
            ol = struct.unpack_from('>H', p, o)[0]; o += 2
            od = None
            if ot in (0, 2): od = p[o:o+ol].hex(); o += ol
            ops.append({"op": {0:"INSERT",1:"DELETE",2:"REPLACE"}[ot],
                       "offset": oo, "length": ol, "data": od})
        result.update(type="DELTA", base_ref=base, op_count=n, operations=ops)
    elif rt == 5:
        n = struct.unpack_from('>H', p, 0)[0]
        entries = []; o = 2
        for _ in range(n):
            s = struct.unpack_from('>I', p, o)[0]; o += 4
            d = struct.unpack_from('>I', p, o)[0]; o += 4
            r = p[o]; o += 1
            ll = p[o]; o += 1
            lb = p[o:o+ll].decode(); o += ll
            entries.append({"source": s, "target": d,
                          "relation": {0:"PARENT",1:"CHILD",2:"SIBLING",3:"ALIAS"}[r],
                          "label": lb})
        result.update(type="XREF", count=n, entries=entries)
    return result


def main():
    sd = os.path.dirname(os.path.abspath(__file__))
    td = os.path.dirname(sd)
    dd = os.path.join(td, "environment", "data")

    s = gen_sample()
    open(os.path.join(dd, "sample.bvault"), 'wb').write(s)
    print(f"sample.bvault: {len(s)} bytes")

    t = gen_test()
    open(os.path.join(sd, "test_archive.bvault"), 'wb').write(t)
    print(f"test_archive.bvault: {len(t)} bytes")

    e = parse_correct(t)
    json.dump(e, open(os.path.join(sd, "expected_output.json"), 'w'), indent=2)
    print("expected_output.json done")


if __name__ == "__main__":
    main()
