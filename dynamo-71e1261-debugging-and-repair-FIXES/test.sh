#!/bin/bash
mkdir -p /logs/verifier
echo "0" > /logs/verifier/reward.txt

# Agent was instructed to run pipeline on eval configs during its turn.
# Verifier only reads pre-existing outputs — never re-runs agent code.
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py /tests/test_outputs_2.py -rA

if [ $? -eq 0 ]; then
  echo "1" > /logs/verifier/reward.txt
else
  echo "0" > /logs/verifier/reward.txt
fi
