# Index bootstrap signing

Whenever there is a new release of the OpenShift we have to release a new version of operator catalog.
This process involves several steps that involves several people and teams.
To reduce amount of manual work we automated the process. One of the steps in the
automation is to sign the catalog image with the Red Hat GPG key.

This document describes how to sign the catalog image with the Red Hat GPG key and
how to use signing automation.

## Prerequisites

- A new version of the index image is available at registry.redhat.io
  - registry.redhat.io/redhat/community-operator-index
  - registry.redhat.io/redhat/certified-operator-index
- An image contains a verion tag - `v4.18` for example
- Access to the OpenShift cluster with Tekton trigger permissions
- `tkn` CLI installed
- A version that needs to be signed can't be already GA and stored in Pyxis indices
  - https://catalog.redhat.com/api/containers/v1/operators/indices
  - If the version is already GA, a workflow needs to be consulted with the Collective team

## Sign the image
The signing process is automated using Tekton pipeline. To trigger a pipeline
a `tkn` cli command needs to be triggered.

First, login to the OpenShift cluster:
```shell
oc login --server=https://api.pipelines-prod.ijdb.p1.openshiftapps.com:6443 --token=<token>
oc project index-bootstrap-prod # or index-bootstrap-stage
```

Then, create a volume claim template:
```shell
cat <<EOF > workspace-template.yaml
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Mi
EOF

```

Then, trigger the pipeline:
```shell
tkn pipeline start \
    index-img-bootstrap-signing-pipeline \
    --use-param-defaults \
    -p image_pullspec=registry.redhat.io/redhat/community-operator-index:v4.18 \
    -p env=prod \
    -p requester=<person or team name> \
    --showlog \
    --workspace name=pipeline,volumeClaimTemplateFile=./workspace-template.yaml
```

The pipeline will sign the image and store the signature to Container sigstore (Pyxis).

#### Stage environment
To sign the image for the stage environment (registry.stage.redhat.io), the `env` parameter
needs to be set to `stage` and signing needs to be done on stage cluster.

```shell
oc login --server=https://api.pipelines-stage.0ce8.p1.openshiftapps.com:6443 --token=<token>
```
