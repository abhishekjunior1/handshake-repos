#!/bin/bash
set -e
echo "0.0" > /logs/verifier/reward.txt

# Test with primary hidden configuration
cp /tests/hidden_data.json /app/input_data.json
cd /app
python3 pipeline.py

pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

# Test with second hidden configuration
cp /tests/hidden_data_2.json /app/input_data.json
python3 pipeline.py

pytest /tests/test_outputs_2.py -rA

echo "1.0" > /logs/verifier/reward.txt
