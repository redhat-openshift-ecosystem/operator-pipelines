# Community pipeline secrets usage

The community pipeline uses a HashiCorp vault collection to store secrets.
Adding new secrets can be achieved using this [guide][1].

The collection is then mounted into the prow job configuration ([example][2]) as
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
[2]: https://github.com/openshift/release/blob/master/ci-operator/config/redhat-openshift-ecosystem/community-operators-pipeline-preprod/redhat-openshift-ecosystem-community-operators-pipeline-preprod-dev__4.10.yaml