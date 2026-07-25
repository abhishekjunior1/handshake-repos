#!/bin/bash
set -e
echo "0.0" > /logs/verifier/reward.txt
cp /tests/hidden_benchmark_config.json /app/benchmark_config.json
cp /tests/hidden_cv_results.json /app/cv_results.json
cd /app
python3 pipeline.py
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
if [ $? -eq 0 ]; then
  echo "1.0" > /logs/verifier/reward.txt
else
  echo "0.0" > /logs/verifier/reward.txt
fi
