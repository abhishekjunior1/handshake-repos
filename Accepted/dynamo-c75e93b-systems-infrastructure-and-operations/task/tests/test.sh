#!/bin/bash
set -e

# Pre-write failure score for graceful failure handling
echo "0.0" > /logs/verifier/reward.txt

# Copy hidden test data as the pipeline input
cp /tests/hidden_metrics.json /app/metrics_input.json

# Run the pipeline on hidden data
cd /app
python3 pipeline.py

# Run verification tests
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo "1.0" > /logs/verifier/reward.txt
else
  echo "0.0" > /logs/verifier/reward.txt
fi
