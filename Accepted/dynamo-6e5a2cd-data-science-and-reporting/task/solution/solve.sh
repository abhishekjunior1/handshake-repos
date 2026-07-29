#!/bin/bash
cd /app
python3 /solution/solve.py
python3 /app/pipeline.py /app/input_data.json /app/output.json
