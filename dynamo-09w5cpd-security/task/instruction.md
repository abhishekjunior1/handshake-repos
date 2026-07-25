A packet authentication system at `/app/main.py` verifies signed SAUTH protocol packets. It uses modules `/app/crypto.py`, `/app/parser.py`, and `/app/verifier.py`.

Run it with `python3 /app/main.py`. It reads packets from `/app/packets.json`, verifies each one, and writes results to `/app/results.json`.

The system works correctly on the current test packets but has bugs that cause it to incorrectly reject valid packets or accept invalid ones on other inputs. Find and fix the bugs so the system correctly handles all valid SAUTH packets.

Do not rewrite from scratch — preserve the existing module structure. The fixed system will be tested on different packets than those at `/app/packets.json`.

Output: `/app/results.json` — JSON array with one object per packet containing `valid` (boolean) and `reason` (string).
