#!/bin/bash

# Copy hidden config into the agent workspace
cp /tests/hidden_network_config.json /app/network_config.json

# Run the pipeline on the hidden config (may fail if agent broke something)
cd /app
python3 /app/pipeline.py || true

# Run pytest verification
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
