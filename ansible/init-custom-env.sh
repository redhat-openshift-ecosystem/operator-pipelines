#!/bin/bash

# Creates service account for each operator-pipeline env; updates secret-vars.yml with token
#
# As arguments, it expects environments for which the sa should be created
#
# ./init-custom-env.sh john-playground qa vault-password
#       creates the pipeline QA resources in oc project john-playground, using file with ansible vault password named vault-password.

set -euo pipefail
umask 077

NAMESPACE=$1
ENV=$2
PIPELINE_IMAGE_TAG=${4:-released}
SECRET=$(dirname "$0")/vaults/custom/ocp-token.yml
PASSWD_FILE=$3

# Initialize the environment by creating the service account and giving for it admin permissions
initialize_environment() {
    if [ ! -f $SECRET ]; then
        touch $SECRET
        echo "File $SECRET was not found, empty one was created"
    fi

    ansible-playbook -i inventory/operator-pipeline playbooks/deploy.yml \
        --vault-password-file=$PASSWD_FILE \
        -e "oc_namespace=$NAMESPACE" \
        -e "env=$ENV" \
        -e "custom=true" \
        -e "ocp_host=`oc whoami --show-server`" \
        -e "ocp_token=`oc whoami -t`" \
        -e "operator_pipeline_image_tag=$PIPELINE_IMAGE_TAG" \
        --tags init \
        -vvvv
}

# Get the token of created service account and make it available for further steps
update_token() {
    local token=$(oc --namespace $NAMESPACE serviceaccounts get-token operator-pipeline-admin)

    echo "ocp_token: $token" > $SECRET
    ansible-vault encrypt $SECRET --vault-password-file $PASSWD_FILE > /dev/null
    echo "Secret file $SECRET was updated and encrypted"
}

# Install all the other resources (pipelines, tasks, secrets etc..)
execute_playbook() {
  ansible-playbook -i inventory/operator-pipeline playbooks/deploy.yml \
    --vault-password-file vault-password \
    -e "oc_namespace=$NAMESPACE" \
    -e "env=$ENV" \
    -e "custom=true"
}

pull_parent_index() {
  oc project $NAMESPACE
  # Must be run once before certifying against the certified catalog.
  oc import-image certified-operator-index \
    --from=registry.redhat.io/redhat/certified-operator-index \
    --reference-policy local \
    --scheduled \
    --confirm \
    --all

  # Must be run once before certifying against the Red Hat Martketplace catalog.
  oc import-image redhat-marketplace-index \
    --from=registry.redhat.io/redhat/redhat-marketplace-index \
    --reference-policy local \
    --scheduled \
    --confirm \
    --all
}

main() {
  initialize_environment
  update_token
  execute_playbook
  pull_parent_index
}

main
