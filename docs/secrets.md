# Community pipeline secrets usage

## Editing secrets
The community pipeline uses a HashiCorp vault collection to store secrets.
Adding new secrets can be achieved using this [guide][1]. If you need to edit
secrets in the community-pipeline collection, you need to ask a maintainer for
access. Note that you can only be added if you have logged in to the [vault
system][3] at least once. After the access is granted, log into the [vault][4]
itself using the OIDC method.

## Collection usage

The collection is mounted into the prow job configuration ([example][2]) as
such:
```yaml
...
- mount_path: /var/run/cred
  name: community-pipeline-github-automation
  namespace: test-credentials
...
```

The secret can then be used in the prow job script. An example with a github
token:
```sh
$ test -f /var/run/cred/operator_bundle_bot_github_token # test if secret exists
$ echo $?
0
$ curl -L -I \
    -u operator-bundle-bot:$(/var/run/cred/operator_bundle_bot_github_token) \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    https://api.github.com/emojis
```

[1]: https://docs.ci.openshift.org/docs/how-tos/adding-a-new-secret-to-ci/
[3]: https://selfservice.vault.ci.openshift.org
[4]: https://vault.ci.openshift.org/ui/
[2]: https://github.com/openshift/release/blob/master/ci-operator/config/redhat-openshift-ecosystem/community-operators-pipeline-preprod/redhat-openshift-ecosystem-community-operators-pipeline-preprod-dev__4.10.yaml
