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

PARAMS="$*"

# parse arguments given to the script
get_environments() {
    if [ -z "$PARAMS" ]; then
        echo "dev stage qa prod"
    else
        echo "$PARAMS"
    fi
}

# execute playbook for given environment
execute_playbook() {
    local secret=$(dirname "$0")/vaults/$env/secret-vars.yml
    if [ ! -f $secret ]; then
        touch $secret
        echo "File $secret was not found, empty one was created"
    fi

    ansible-playbook -i inventory/operator-pipeline playbooks/deploy.yml \
        --vault-password-file=$2 \
        -e "env=$1" \
        -e "ocp_host=`oc whoami --show-server`" \
        -e "ocp_token=`oc whoami -t`" \
        --tags init \
        -vvvv
}

# update token for given environment
update_token() {
    # In openshift 4.11 we don't have `oc serviceaccount get-token` anymore
    # because of the changes in the SA token API in k8s 1.24.
    local token=$(oc --namespace operator-pipeline-$1 get secret \
        -o custom-columns=NAME:.metadata.name,TYPE:.type,TOKEN:.data.token \
        | awk '$2=="kubernetes.io/service-account-token" && $1~/^operator-pipeline-admin-token/ {print $3; exit}' \
        | base64 -d)

    local secret=$(dirname "$0")/vaults/$env/secret-vars.yml

    echo "ocp_token: $token" > $secret
    ansible-vault encrypt $secret --vault-password-file $2 > /dev/null
    echo "Secret file $secret was updated and encrypted"

}

main() {

    local environments=$(get_environments)
    local passwd_file=./vault-password

    # Executes the playbook for each env
    for env in $environments;
    do
        execute_playbook $env $passwd_file
    done

    # Asks if the script should update the secret-vars.yml files
    read -p "Service accounts configured for ($environments). Update secret-vars with tokens? [y/N] " -n 1 -r
    echo

    # Updates the secret-vars.yml files
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        for env in $environments; do
            update_token $env $passwd_file
        done
    fi
}

main
