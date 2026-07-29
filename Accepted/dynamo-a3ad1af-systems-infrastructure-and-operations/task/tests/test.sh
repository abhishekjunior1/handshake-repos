#!/bin/bash
# Copy hidden test data into the app directory
cp /tests/hidden_topology.json /app/hidden_topology.json
cp /tests/hidden_config.json /app/config.json

# Run the pipeline with hidden data
python3 /app/pipeline.py /app/config.json /app/output.json

# Run pytest verification
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
