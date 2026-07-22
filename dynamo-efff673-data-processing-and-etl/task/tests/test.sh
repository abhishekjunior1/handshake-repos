#!/bin/bash
set -e

# Pre-write failure score
echo "0.0" > /logs/verifier/reward.txt

# Substitute hidden data for verification
cp /tests/hidden_stream_config.json /app/stream_config.json

# Run the pipeline
cd /app
python3 pipeline.py

# Run verification tests
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo "1.0" > /logs/verifier/reward.txt
else
  echo "0.0" > /logs/verifier/reward.txt
fi
