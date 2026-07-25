#!/bin/bash

# Pre-write failure score
echo "0.0" > /logs/verifier/reward.txt

# Hide expected output during pipeline execution
mv /tests/expected_output.json /tmp/expected_output.json

# Copy hidden test configuration
cp /tests/hidden_config.json /app/config.json

# Execute the pipeline
cd /app
python3 pipeline.py || { mv /tmp/expected_output.json /tests/expected_output.json; exit 0; }

# Restore expected output for verification
mv /tmp/expected_output.json /tests/expected_output.json

# Run verification tests
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
if [ $? -eq 0 ]; then
    echo "1.0" > /logs/verifier/reward.txt
fi
