"""SAUTH packet verification pipeline."""
import json
import sys

from parser import parse_packet
from verifier import verify_packet

KEY_PATH = "/app/key.bin"
INPUT_PATH = "/app/packets.json"
OUTPUT_PATH = "/app/results.json"


def load_key():
    with open(KEY_PATH, "rb") as f:
        return f.read()


def run(input_path=INPUT_PATH, output_path=OUTPUT_PATH):
    key = load_key()
    packets_hex = json.load(open(input_path))

    # Parse all packets
    parsed = []
    for i, pkt_hex in enumerate(packets_hex):
        raw = bytes.fromhex(pkt_hex)
        pkt, err = parse_packet(raw)
        if err:
            parsed.append((i, None, err))
        else:
            parsed.append((i, pkt, None))

    # Sort by timestamp for replay detection ordering
    valid_packets = [(i, pkt) for i, pkt, err in parsed if err is None]
    valid_packets.sort(key=lambda x: x[1]["timestamp"])

    # Replay detection: sequence numbers must be strictly increasing
    results = {}
    last_seq = -1
    for i, pkt in valid_packets:
        ok, reason = verify_packet(key, pkt)
        if ok:
            if pkt["seq"] <= last_seq:
                results[i] = {"valid": False, "reason": "replay_detected"}
            else:
                results[i] = {"valid": True, "reason": "valid"}
                last_seq = pkt["seq"]
        else:
            results[i] = {"valid": False, "reason": reason}

    # Add parse failures
    for i, pkt, err in parsed:
        if err is not None:
            results[i] = {"valid": False, "reason": err}

    # Output in original order
    output = [results[i] for i in range(len(packets_hex))]
    json.dump(output, open(output_path, "w"), indent=2)
    for i, r in enumerate(output):
        status = "PASS" if r["valid"] else "FAIL"
        print(f"  [{i}] {status} — {r['reason']}")


if __name__ == "__main__":
    run()
