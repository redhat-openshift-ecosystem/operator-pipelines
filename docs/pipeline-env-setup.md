# Pipeline Environment Setup

[Common for all the pipelines](#common-for-all-the-pipelines)

[Only CI Pipeline](#only-ci-pipeline)

[Only Hosted Pipeline](#only-hosted-pipeline)

[Only Release Pipeline](#only-release-pipeline)

## Common for all the pipelines:

### Red Hat Catalog Imagestreams

The pipelines must pull the parent index images through the internal OpenShift
registry to take advantage of the built-in credentials for Red Hat's terms-based
registry (registry.redhat.io). This saves the user from needing to provide such
credentials. The index generation task will always pull published index images
through imagestreams of the same name in the current namespace. As a result,
there is a one time configuration for each desired distribution catalog. Replace
the `from` argument when configuring this for pre-production environments.

```bash
# Must be run once before certifying against the certified catalog.
oc --request-timeout 10m import-image certified-operator-index \
  --from=registry.redhat.io/redhat/certified-operator-index \
  --reference-policy local \
  --scheduled \
  --confirm \
  --all

# Must be run once before certifying against the Red Hat Marketplace catalog.
oc --request-timeout 10m import-image redhat-marketplace-index \
  --from=registry.redhat.io/redhat/redhat-marketplace-index \
  --reference-policy local \
  --scheduled \
  --confirm \
  --all
```

## Only CI pipeline:

### Registry Credentials
The CI pipeline can optionally be configured to push and pull images to/from a remote
private registry. The user must create an auth secret containing the docker config.
This secret can then be passed as a workspace named `registry-credentials` when invoking
the pipeline.

```bash
oc create secret generic registry-dockerconfig-secret \
  --type kubernetes.io/dockerconfigjson \
  --from-file .dockerconfigjson=config.json
```

### Git SSH Secret
The pipelines requires git SSH credentials with 
write access to the repository if automatic digest pinning
is enabled using the pin_digests param. This is disabled
by default. Before executing the pipeline the user must
create a secret in the same namespace as the pipeline.

To create the secret run the following commands (substituting your key):
```bash
cat << EOF > ssh-secret.yml
kind: Secret
apiVersion: v1
metadata:
  name: github-ssh-credentials
data:
  id_rsa: |
    < PRIVATE SSH KEY >
EOF

oc create -f ssh-secret.yml
```

### Container API access
CI pipelines automatically upload a test results, logs and artifacts using Red Hat
container API. This requires a partner's API key and the key needs to be created
as a secret in OpenShift cluster before running a Tekton pipeline.

```bash
oc create secret generic pyxis-api-secret --from-literal pyxis_api_key=< API KEY >
```

### Kubeconfig

The CI pipeline requires a kubeconfig with admin credentials. This can be created
by logging into said cluster as an admin user.

```bash
KUBECONFIG=kubeconfig oc login -u <username> -p <password>
oc create secret generic kubeconfig --from-file=kubeconfig=kubeconfig
```

### GitHub API token
To automatically open the PR with submission, pipeline must authenticate to GitHub. 
Secret containing api token should be created.

```bash
oc create secret generic github-api-token --from-literal GITHUB_TOKEN=< GITHUB TOKEN >
```

## Only Hosted pipeline:

### Registry Credentials
The hosted pipeline requires credentials to push/pull bundle and index images from a
pre-release registry (quay.io). A registry auth secret must be created. This secret
can then be passed as a workspace named `registry-credentials` when invoking
the pipeline.

```bash
oc create secret generic hosted-pipeline-registry-auth-secret \
  --type kubernetes.io/dockerconfigjson \
  --from-file .dockerconfigjson=config.json
```

### Container API access
The hosted pipeline communicates with internal Container API that requires cert + key.
The corresponding secret needs to be created before running the pipeline.

```bash
oc create secret generic operator-pipeline-api-certs \
  --from-file operator-pipeline.pem \
  --from-file operator-pipeline.key
```

### Hydra credentials
To verify publishing checklist, Hosted pipeline uses Hydra API. To authenticate with
Hydra over basic auth, secret containing service account credentials should be created.

```bash
oc create secret generic hydra-credentials \
  --from-literal username=<username>  \
  --from-literal password=<password>
```

### GitHub Bot token
To automatically merge the PR, Hosted pipeline uses GitHub API. To authenticate
when using this method, secret containing bot token should be created.

```bash
oc create secret generic github-bot-token --from-literal github_bot_token=< BOT TOKEN >
```

### Prow-kubeconfig
Hosted preflight tests are run on the separate cluster. To provision a cluster destined for the tests,
the pipeline uses a Prowjob. Thus, to start the preflight test, there needs to be a prow-specific
kubeconfig.
- [ProwJob](https://github.com/kubernetes/test-infra/tree/master/prow)
- [OperatorCI](https://docs.ci.openshift.org/docs/architecture/ci-operator/)
```bash
oc create secret generic prow-kubeconfig \
  --from-literal kubeconfig=<kubeconfig>
```

### Preflight decryption key
Results of the preflight tests are protected by encryption. In order to retrieve them
from the preflight job, gpg decryption key should be supplied.
```bash
oc create secret generic preflight-decryption-key \
  --from-literal private=<private gpg key> \
  --from-literal public=<public gpg key>
```

### OCP-registry-kubeconfig
OCP clusters contains the public registries for Operator Bundle Images.
To publish the image to this registry, Pipeline connects to OCP cluster via
kubeconfig.
To create the secret which contains the OCP cluster kubeconfig:
```bash
oc create secret generic ocp-registry-kubeconfig \
  --from-literal kubeconfig=<kubeconfig>
```

### Quay OAuth Token
A Quay OAuth token is required to set repo visibility to public.
```bash
oc create secret generic quay-oauth-token --from-literal token=<token>
```

## Only Release pipeline:

### Registry Credentials
The release pipeline requires credentials to push and pull the bundle image built by
the hosted pipeline. Three registry auth secrets must be specified since different
credentials may be required for the same registry when copying and serving the image.
These secrets can then be passed as workspaces named `registry-pull-credentials`,
`registry-push-credentials` and `registry-serve-credentials` when invoking the
pipeline.

```bash
oc create secret generic release-pipeline-registry-auth-pull-secret \
  --type kubernetes.io/dockerconfigjson \
  --from-file .dockerconfigjson=pull-config.json

oc create secret generic release-pipeline-registry-auth-push-secret \
  --type kubernetes.io/dockerconfigjson \
  --from-file .dockerconfigjson=push-config.json

oc create secret generic release-pipeline-registry-auth-serve-secret \
  --type kubernetes.io/dockerconfigjson \
  --from-file .dockerconfigjson=serve-config.json
```

### Kerberos credentials
For submitting the IIB build, you need kerberos keytab in a secret:
```bash
oc create secret generic kerberos-keytab \
  --from-file krb5.keytab
```

### Quay credentials
Release pipeline uses Quay credentials to authenticate a push to an index image
during the IIB build.
```bash
oc create secret generic iib-quay-credentials \
  --from-literal username=<QUAY_USERNAME> \
  --from-literal password=<QUAY_PASSWORD>
```

### OCP-registry-kubeconfig
OCP clusters contains the public registries for Operator Bundle Images.
To publish the image to this registry, Pipeline connects to OCP cluster via
kubeconfig.
To create the secret which contains the OCP cluster kubeconfig:
```bash
oc create secret generic ocp-registry-kubeconfig \
  --from-literal kubeconfig=<kubeconfig>
```

Additional setup instructions for this cluster are documented [here](rhc4tp-cluster.md).

