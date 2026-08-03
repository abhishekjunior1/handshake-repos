#!/bin/bash
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt
echo "0" > /logs/verifier/reward.txt
python3 -S /tests/verifier_harness.py
python3 -S /tests/run_pytest.py --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py /tests/test_outputs_2.py /tests/test_outputs_3.py -rA
rc=$?
rm -f /logs/verifier/reward.txt
if [ "$rc" -eq 0 ]; then
  echo "1" > /logs/verifier/reward.txt
else
  echo "0" > /logs/verifier/reward.txt
fi
exit 0
