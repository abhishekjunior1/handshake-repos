#!/bin/bash
set -e
echo "0.0" > /logs/verifier/reward.txt

cp /tests/hidden_input.json /app/input.json
cd /app
python3 pipeline.py
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

cp /tests/hidden_input_2.json /app/input.json
python3 pipeline.py
pytest /tests/test_outputs_2.py -rA

echo "1.0" > /logs/verifier/reward.txt
