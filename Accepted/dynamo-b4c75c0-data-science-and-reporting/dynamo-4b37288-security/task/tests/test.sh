#!/bin/bash

mkdir -p /logs/verifier

# Copy hidden test archive
cp /tests/test_archive.bvault /app/sample.bvault

# Run the parser
cd /app
python3 main.py sample.bvault output.json 2>/dev/null || true

# Run pytest
if pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
