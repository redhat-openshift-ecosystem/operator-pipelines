#!/usr/bin/env bash

set -e

usage() {
  echo "Usage: $0
  [ -i BUNDLE_IMAGE a pull spec to a bundle image to copy ]
  [ -n PKG_NAME the new operator package name ]
  [ -v BUNDLE_VERSION the new operator version ]
  [ -r OCP_RANGE the new supported OpenShift version range (see: https://url.corp.redhat.com/6e0ad44) ]
  [ -o OUTPUT_PATH a directory for the generated structure ]
  [ -h show this usage ]" 1>&2
}

# Image with the `yq` utility installed
YQ_IMG=quay.io/redhat-isv/operator-pipelines-images:latest

# Default CLI arg values
BUNDLE_IMAGE="quay.io/operator-pipeline-stage/test-e2e-operator:0.0.7"
PKG_NAME="test-operator-$(whoami)"
OCP_RANGE="v4.7"
BUNDLE_VERSION="0.0.1"
OUTPUT_PATH="."

# Parse optional CLI args
while getopts ":i:n:v:r:o:h:" opt; do
  case $opt in
    i) BUNDLE_IMAGE=$OPTARG;;
    n) PKG_NAME=$OPTARG;;
    v) BUNDLE_VERSION=$OPTARG;;
    r) OCP_RANGE=$OPTARG;;
    o) OUTPUT_PATH=$OPTARG;;
    h) usage && exit 0;;
    *) usage && exit 1;;
  esac
done

echo "Copying Operator bundle image: $BUNDLE_IMAGE"
echo "New bundle version: $BUNDLE_VERSION"
echo "New package name: $PKG_NAME"
echo "New OCP version range: $OCP_RANGE"
echo "Output path: $OUTPUT_PATH"

podman pull $BUNDLE_IMAGE

DEST="$(realpath $OUTPUT_PATH)/$PKG_NAME/$BUNDLE_VERSION"
mkdir -p $DEST

# Command to run with `podman unshare`
# Mounts the filesystem of the bundle image to the local system
# Corrects the directory permissions so they can be accessed
UNSHARE_CMD=$(cat <<EOF
cp -r \$(podman image mount $BUNDLE_IMAGE)/. $DEST;
find $DEST -type d -exec chmod 755 {} \;
EOF
)

# Extract the content of the bundle image
podman unshare bash -c "$UNSHARE_CMD"

# YQ expression to modify the CSV
CSV_YQ_EXPR=".spec.version=\"$BUNDLE_VERSION\" \
  | .metadata.name=\"$PKG_NAME.$BUNDLE_VERSION\" \
  | del(.spec.replaces)"

# YQ expression to modify the annotations
ANNOTATIONS_YQ_EXPR=".annotations.\"com.redhat.openshift.versions\"=\"$OCP_RANGE\" \
  | .annotations.\"operators.operatorframework.io.bundle.package.v1\"=\"$PKG_NAME\""

MANIFESTS="$DEST/manifests"
CSV=$(realpath "$MANIFESTS/*.clusterserviceversion.y*ml")
ANNOTATIONS=$(realpath "$DEST/metadata/annotations.y*ml")
MNT_PATH="/tmp/manifests"

# Generate a replacement clusterserviceversion YAML
NEW_CSV=$(
  podman run --rm \
    -v $DEST/manifests:$MNT_PATH:Z \
    $YQ_IMG \
    yq -y "$CSV_YQ_EXPR" "$MNT_PATH/$(basename $CSV)"
)

# Generate a replacement annotations YAML
NEW_ANNOTATIONS=$(
  podman run --rm \
    -v $DEST/metadata:$MNT_PATH:Z \
    $YQ_IMG \
    yq -y "$ANNOTATIONS_YQ_EXPR" "$MNT_PATH/$(basename $ANNOTATIONS)"
)

# Save the modifications
# Replace the CSV to match the package name
rm $CSV
echo "$NEW_CSV" > "$MANIFESTS/$PKG_NAME.clusterserviceversion.yaml"
echo "$NEW_ANNOTATIONS" > $ANNOTATIONS

echo "Successfully created bundle directory: $DEST"
