#!/bin/bash
set -e

mkdir -p /logs/verifier
echo "0.0" > /logs/verifier/reward.txt

cp /tests/hidden_network_config.json /app/network_config.json
cp /tests/expected_output.json /app/expected_output.json

cd /app
python3 pipeline.py

if pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA; then
    echo "1.0" > /logs/verifier/reward.txt
fi
