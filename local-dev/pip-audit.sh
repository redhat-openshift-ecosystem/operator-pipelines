#!/usr/bin/env bash
# remove any previous runs to ensure isolated run
rm -f /tmp/audit-output.json
# run pip-audit on dependencies, output to json file, mask any failures
pip-audit -r /tmp/requirements.txt --format=json -o /tmp/audit-output.json || true
