#!/bin/bash
set -uo pipefail

cp /tests/hidden_taskfile.json /app/taskfile.json
cd /app
python3 runner.py taskfile.json /app/output.json

pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py /tests/test_runner.py -rA -v

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
