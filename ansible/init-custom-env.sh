#!/bin/bash

# Creates service account for each operator-pipeline env; updates secret-vars.yml with token
#
# As arguments, it expects environments for which the sa should be created
#
# ./init.sh dev stage prod
#       creates the sa for dev, stage and prod environments
# ./init.sh
#       creates the sa for every environment (prod, stage, qa, dev)

set -euo pipefail
umask 077

NAMESPACE=$1
ENV=$2
SECRET=$(dirname "$0")/vaults/custom/secret-vars.yml
PASSWD_FILE=./vault-password

# execute playbook for given environment
execute_playbook() {
    if [ ! -f $SECRET ]; then
        touch $SECRET
        echo "File $SECRET was not found, empty one was created"
    fi

    ansible-playbook -i inventory/operator-pipeline playbooks/deploy.yml \
        --vault-password-file=$PASSWD_FILE \
        -e "namespace=$NAMESPACE" \
        -e "env=$ENV" \
        -e "custom=true" \
        -e "ocp_host=`oc whoami --show-server`" \
        -e "ocp_token=`oc whoami -t`" \
        --tags init \
        -vvvv
}

# update token for given environment
update_token() {
    local token=$(oc --namespace $NAMESPACE serviceaccounts get-token operator-pipeline-admin)

    echo "ocp_token: $token" > $SECRET
    ansible-vault encrypt $SECRET --vault-password-file $PASSWD_FILE > /dev/null
    echo "Secret file $SECRET was updated and encrypted"

}

main() {
    # Executes the playbook
    execute_playbook

    # Asks if the script should update the secret-vars.yml files
    read -p "Service accounts configured for custom namespace ($NAMESPACE). Update secret-vars with tokens? [y/N] " -n 1 -r
    echo

    # Updates the secret-vars.yml file
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      update_token
    fi
}

main
