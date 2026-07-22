#!/bin/bash
set -e

echo "0.0" > /logs/verifier/reward.txt

# Copy hidden test data into the pipeline's working directory
cp /tests/hidden_sensor_config.json /app/sensor_config.json

# Run the pipeline
cd /app
python3 pipeline.py

# Run verification tests (disable set -e for pytest to capture exit code)
set +e
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
RESULT=$?
set -e

if [ $RESULT -eq 0 ]; then
    echo "1.0" > /logs/verifier/reward.txt
else
    echo "0.0" > /logs/verifier/reward.txt
fi
