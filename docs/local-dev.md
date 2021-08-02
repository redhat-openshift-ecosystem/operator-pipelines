# Local development of the operator-pipelines-images

Development of the Python script doesn't demand any sophisticated strategy. However, before adding the script to release branch,
in order to test them they must run within the pipeline.

## Prerequisites

1. Install [Buildah](https://github.com/containers/buildah/blob/main/install.md)
2. Setup [operator-pipelines](https://github.com/redhat-openshift-ecosystem/operator-pipelines/blob/main/docs/local-dev.md)

## Initial Setup
1. If you are adding a new script- don't forget to add the entrypoint to setup.py
2. Build the image containing the script via Buildah
```bash
buildah bud
```
3. Push the image to registry, eg. Quay.io.
```bash
buildah push <image signature- output of build step> <path in registry> 
```   
This step may require login, eg.
```bash
buildah login quay.io
```
4. In [operator-pipelines](https://github.com/redhat-openshift-ecosystem/operator-pipelines), change the base image of script that
was changed, to the one pushed in the previous step.
   
5. Run the pipeline and test if the results are as expected.