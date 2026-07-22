#!/bin/bash
# Copy hidden test data to /app (replacing visible data)
cp /tests/hidden_dataset.json /app/dataset.json
cp /tests/hidden_schema.json /app/schema.json

# Run the pipeline with hidden data
cd /app && python3 pipeline.py

# Run pytest to verify output matches expected
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
