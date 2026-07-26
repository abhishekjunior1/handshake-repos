#!/bin/bash
mkdir -p /logs/verifier

echo "0" > /logs/verifier/reward.txt

# The agent was instructed to run pipeline on eval_taskfile.json during its turn
# and write results to /app/output_eval.json.
# The verifier only reads those outputs — it never re-runs agent code.
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo "1" > /logs/verifier/reward.txt
fi
