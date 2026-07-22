#!/bin/bash

# Copy hidden test configuration to the app directory
cp /tests/hidden_config.json /app/config.json

# Hide ground truth while pipeline runs to prevent reward hacking
mv /tests/expected_output.json /tmp/_ground_truth.json

# Run the pipeline with hidden config (may fail if bugs not fixed)
cd /app && python3 pipeline.py config.json /app/output.json || true

# Restore ground truth for pytest comparison
mv /tmp/_ground_truth.json /tests/expected_output.json

# Run pytest verification
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
