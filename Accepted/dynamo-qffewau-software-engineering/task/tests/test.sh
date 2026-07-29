#!/bin/bash
mkdir -p /logs/verifier

# Default to failure — reward is always written
echo "0" > /logs/verifier/reward.txt

# Run pytest against the agent's pre-existing outputs.
# The agent was instructed to run runner.py on all eval taskfiles during its turn
# and write results to /app/output_eval_1.json and /app/output_eval_2.json.
# The verifier only reads those outputs — it never re-runs agent code.
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo "1" > /logs/verifier/reward.txt
else
  echo "0" > /logs/verifier/reward.txt
fi
