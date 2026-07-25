A cryptographic envelope pipeline at `/app/pipeline.py` processes message configurations into sealed envelopes. It uses modules `/app/key_derivation.py`, `/app/block_cipher.py`, `/app/mac_engine.py`, `/app/envelope_builder.py`, and `/app/padding.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current configuration but has bugs that cause incorrect results on other configurations. Find and fix the bugs so the pipeline handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure and the key schedule's rotation-based diffusion and the PKCS#7 convention of always adding padding (full block when already aligned). The fixed pipeline will be tested on a different configuration than the one at `/app/config.json`.

Output: `/app/output.json` — a JSON object with keys `pipeline_version`, `num_messages`, `key_derivation` (containing `enc_fingerprint` and `mac_fingerprint`), and `envelopes` (array of objects each with `message_id`, `sender`, `recipient`, `envelope_hex`, `envelope_size`, `envelope_digest`, `ciphertext_length`, `mac_tag_hex`, `enc_key_fingerprint`, `mac_key_fingerprint`).
