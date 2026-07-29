#!/bin/bash

mkdir -p /logs/verifier

cp /tests/hidden_source.json /app/data/source.json

cd /app/data
python3 pipeline.py || true

cd /tests
python3 -m pytest test_outputs.py -v
RESULT=$?

if [ $RESULT -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
