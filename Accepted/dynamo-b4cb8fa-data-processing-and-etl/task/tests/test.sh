#!/bin/bash
# Copy hidden config to pipeline's input location
cp /tests/eval_config_hidden.json /app/transform_config.json

# Run the pipeline on hidden data
python3 /app/pipeline.py /app/transform_config.json /app/output.json

# Run pytest verification
pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
