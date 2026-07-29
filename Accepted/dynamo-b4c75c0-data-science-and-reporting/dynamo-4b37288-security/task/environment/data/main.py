"""BinVault archive extraction."""
import json
import struct
import sys
import zlib

from parser import parse_record
from checksum import verify
from encoding import decode_data

HEADER_FMT = '>4sHHIQI'
HEADER_SIZE = 24


def extract(input_path, output_path):
    with open(input_path, 'rb') as f:
        data = f.read()

    # Parse header
    magic, ver, flags, count, ts, hdr_crc = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])
    if magic != b'BVLT':
        print("bad magic", file=sys.stderr); sys.exit(1)

    # Parse records
    offset = HEADER_SIZE
    records = []
    for i in range(count):
        rec, offset, err = parse_record(data, offset)
        if err:
            records.append({"record_index": i, "type": "ERROR", "error": err, "_sort": 0xFF})
            break
        try:
            records.append(decode_record(rec, i))
        except Exception as e:
            records.append({"record_index": i, "type": "ERROR", "error": str(e), "_sort": 0xFF})
            break

    # Sort by type code for grouped output
    records.sort(key=lambda r: r.get("_sort", 0))
    for r in records:
        r.pop("_sort", None)

    types = {}
    for r in records:
        t = r.get("type", "?")
        types[t] = types.get(t, 0) + 1

    output = {
        "archive": {"file": input_path.split("/")[-1], "size": len(data),
                    "version": ver, "flags": flags, "records": count, "timestamp": ts},
        "records": records,
        "summary": {"total": len(records), "types": types,
                    "errors": sum(1 for r in records if r["type"] == "ERROR")}
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Parsed: {len(records)} records, {output['summary']['errors']} errors")
    if output["summary"]["errors"]:
        sys.exit(1)


def decode_record(rec, idx):
    t = rec["type"]
    p = rec["payload"]
    result = {"record_index": idx, "flags": rec["flags"], "_sort": t}

    if t == 0x01:  # METADATA
        kl = struct.unpack_from('>H', p, 0)[0]
        key = p[2:2+kl].decode()
        vl = struct.unpack_from('>H', p, 2+kl)[0]
        val = p[4+kl:4+kl+vl].decode()
        result.update(type="METADATA", key=key, value=val)

    elif t == 0x02:  # BLOB
        bid = struct.unpack_from('>I', p, 0)[0]
        enc = p[4]
        dl = struct.unpack_from('>I', p, 5)[0]
        raw = p[9:9+dl]
        crc = struct.unpack_from('>I', p, 9+dl)[0]
        ok = verify(raw, enc, crc)
        decoded = decode_data(raw, enc)
        result.update(type="BLOB", blob_id=bid, encoding=enc,
                     data_length=len(decoded), preview=decoded[:64].hex(),
                     checksum_valid=ok, checksum_stored=crc)

    elif t == 0x03:  # INDEX
        n = struct.unpack_from('>H', p, 0)[0]
        entries = []
        off = 2
        for _ in range(n):
            ref = struct.unpack_from('>I', p, off)[0]; off += 4
            pos = struct.unpack_from('>I', p, off)[0]; off += 4
            entries.append({"ref": ref, "offset": pos})
        result.update(type="INDEX", count=n, entries=entries)

    elif t == 0x04:  # DELTA
        base = struct.unpack_from('>I', p, 0)[0]
        n = struct.unpack_from('>H', p, 4)[0]
        ops = []
        off = 6
        for _ in range(n):
            if off >= len(p): break
            ot = p[off]; off += 1
            oo = struct.unpack_from('>I', p, off)[0]; off += 4
            ol = struct.unpack_from('>H', p, off)[0]; off += 2
            od = None
            if ot in (0, 2):
                od = p[off:off+ol].hex(); off += ol
            ops.append({"op": {0:"INSERT",1:"DELETE",2:"REPLACE"}.get(ot,"?"),
                       "offset": oo, "length": ol, "data": od})
        result.update(type="DELTA", base_ref=base, op_count=n, operations=ops)

    elif t == 0x05:  # XREF
        n = struct.unpack_from('>H', p, 0)[0]
        entries = []
        off = 2
        for _ in range(n):
            if off >= len(p): break
            s = struct.unpack_from('>I', p, off)[0]; off += 4
            d = struct.unpack_from('>I', p, off)[0]; off += 4
            r = p[off]; off += 1
            ll = p[off]; off += 1
            lb = p[off:off+ll].decode(); off += ll
            entries.append({"source": s, "target": d,
                          "relation": {0:"PARENT",1:"CHILD",2:"SIBLING",3:"ALIAS"}.get(r,"?"),
                          "label": lb})
        result.update(type="XREF", count=n, entries=entries)
    else:
        result.update(type="UNKNOWN")

    return result


if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv) > 1 else "/app/sample.bvault"
    out = sys.argv[2] if len(sys.argv) > 2 else "/app/output.json"
    extract(inp, out)
