#!/bin/bash
# Runs inside the SHARED environment image — canonical TB2.
# Copies hidden config, runs pipeline, then verifies output with pytest.

# Copy hidden test data to the app directory
cp /tests/hidden_config.nconf /app/config.nconf

# Run the pipeline on hidden data
cd /app && python3 pipeline.py

# Run pytest verification
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
