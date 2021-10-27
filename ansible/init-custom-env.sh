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

# execute playbook for given environment
execute_playbook() {
    local secret=$(dirname "$0")/vaults/custom/secret-vars.yml
    if [ ! -f $secret ]; then
        touch $secret
        echo "File $secret was not found, empty one was created"
    fi

    ansible-playbook -i inventory/operator-pipeline playbooks/deploy.yml \
        --vault-password-file=$3 \
        -e "namespace=$1" \
        -e "env=$2" \
        -e "custom=true" \
        -e "ocp_host=`oc whoami --show-server`" \
        -e "ocp_token=`oc whoami -t`" \
        --tags init \
        -vvvv
}

# update token for given environment
update_token() {
    local token=$(oc --namespace $1 serviceaccounts get-token operator-pipeline-admin)
    local secret=$(dirname "$0")/vaults/custom/secret-vars.yml

    echo "ocp_token: $token" > $secret
    ansible-vault encrypt $secret --vault-password-file $2 > /dev/null
    echo "Secret file $secret was updated and encrypted"

}

main() {

    local passwd_file=./vault-password

    # Executes the playbook for each env
    execute_playbook $NAMESPACE $ENV $passwd_file

    # Asks if the script should update the secret-vars.yml files
    read -p "Service accounts configured for custom namespace ($NAMESPACE). Update secret-vars with tokens? [y/N] " -n 1 -r
    echo

    # Updates the secret-vars.yml files
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        for env in $environments; do
            update_token $env $passwd_file
        done
    fi
}

main
