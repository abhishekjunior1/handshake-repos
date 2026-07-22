#!/bin/bash
set -e
echo '0.0' > /logs/verifier/reward.txt
cp /tests/hidden_data.json /app/input_data.json
cd /app
python3 pipeline.py
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
if [ $? -eq 0 ]; then
  echo '1.0' > /logs/verifier/reward.txt
fi
