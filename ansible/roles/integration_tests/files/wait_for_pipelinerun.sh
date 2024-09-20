#!/bin/bash
PIPELINE_RUN_NAME=$1
NAMESPACE=$2

if [ -z "$PIPELINE_RUN_NAME" ] || [ -z "$NAMESPACE" ]; then
echo "Usage: $0 <pipeline-run-name> <namespace>"
exit 1
fi

get_pipeline_status() {
    oc get pipelinerun "$PIPELINE_RUN_NAME" -n "$NAMESPACE" -o json | jq -r '.status.conditions[] | select(.type=="Succeeded") | .status'
}

while true; do
    STATUS=$(get_pipeline_status)

    if [ "$STATUS" == "True" ]; then
        echo "PipelineRun $PIPELINE_RUN_NAME succeeded."
        exit 0
    elif [ "$STATUS" == "False" ]; then
        echo "PipelineRun $PIPELINE_RUN_NAME failed."
        exit 1
    else
        echo "PipelineRun $PIPELINE_RUN_NAME is still running..."
    fi
    sleep 20
done