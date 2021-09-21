
## Cluster resources to create

[Common for all the pipelines](#common-for-all-the-pipelines)

[Only CI Pipeline](#only-ci-pipeline)

[Only Hosted Pipeline](#only-hosted-pipeline)


### Common for all the pipelines:

#### Registry Credentials
The pipelines can optionally be configured to push images to a remote private
registry. The user must create an auth secret containing the docker config. This
secret can then be passed as a workspace named `registry-credentials` when invoking
the pipeline.

```bash
cat << EOF > registry-secret.yml
apiVersion: v1
kind: Secret
metadata:
  name: registry-dockerconfig-secret
data:
  .dockerconfigjson: < BASE64 ENCODED DOCKER CONFIG >
type: kubernetes.io/dockerconfigjson
EOF

oc create -f registry-secret.yml
```

#### Red Hat Catalog Imagestreams

The pipelines must pull the parent index images through the internal OpenShift
registry to take advantage of the built-in credentials for Red Hat's terms-based
registry (registry.redhat.io). This saves the user from needing to provide such
credentials. The index generation task will always pull published index images
through imagestreams of the same name in the current namespace. As a result,
there is a one time configuration for each desired distribution catalog.

```bash
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
```

### Only CI pipeline:

#### Git SSH Secret
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

#### Container API access
CI pipelines automatically upload a test results, logs and artifacts using Red Hat
container API. This requires a partner's API key and the key needs to be created
as a secret in openshift cluster before running a Tekton pipeline.

```bash
oc create secret generic pyxis-api-secret --from-literal pyxis_api_key=< API KEY >
```

#### Kubeconfig

The CI pipeline requires a kubeconfig with admin credentials. This can be created
by logging into said cluster as an admin user.

```bash
KUBECONFIG=kubeconfig oc login -u <username> -p <password>
oc create secret generic kubeconfig --from-file=kubeconfig=kubeconfig
```

#### GitHub Bot token
To automatically merge the PR, Hosted pipeline uses GitHub API. To authenticate
when using this method, secret containing bot token should be created.

```bash
oc create secret generic github-bot-token --from-literal github_bot_token=< BOT TOKEN >
```

### Only Hosted pipeline:
#### Container API access
The hosted pipeline communicates with internal Container API that requires cert + key.
The corresponding secret needs to be created before running the pipeline.

```bash
oc create secret generic operator-pipeline-api-certs \
  --from-file operator-pipeline.pem \
  --from-file operator-pipeline.key
```

#### Hydra credentials
To verify publishing checklist, Hosted pipeline uses Hydra API. To authenticate with
Hydra over basic auth, secret containing service account credentials should be created.

```bash
oc create secret generic hydra-credentials \
  --from-literal username=<username>  \
  --from-literal password=<password>
```

#### Service account permissions

Openshift Pipelines are using self- created service account named Pipeline. 
To grant permissions to create new namespaces, run:
```bash
oc secret link pipeline registry-dockerconfig-secret
```
To grant permissions to pull images from specified registries by service account, run
```bash
oc adm policy add-cluster-role-to-user self-provisioner -z pipeline -n <YOUR_NAMESPACE> 
```