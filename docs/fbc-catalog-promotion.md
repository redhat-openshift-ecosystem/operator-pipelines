# FBC catalog promotion

Every couple of months when OpenShift releases a new version, operators needs to be promoted from
the previous version to the new one. In the non-FBC mode this is done at the time
of the index image bootstrapping. Based on the annotation `com.redhat.openshift.versions`
the operator is promoted to the next version.

In the FBC mode the process is a bit different, as a source of the catalog is
stored in the git repository. The process of promoting the operator to the next version
is driven by the semi-automated process.

## FBC catalog promotion process

Before an Openshift version `N` is GA and index image `N+1` is ready, the operator
pipeline maintainers needs to prepare the operator for the next version. The automated
script will create a pull request with the changes needed to promote the operator
to the next version.

Based on the FBC configuration in the `ci.yaml` file, the script will exectute
the following steps:
- Detect FBC onboarder operators `fbc.enabled: true`
- Detect the `fbc.version_promotion_strategy` option
- Copy catalog from `N` to `N+1` within the `catalogs` directory
- Update the `catalog_mapping` in the `ci.yaml` file

Based on the `fbc.version_promotion_strategy` option, the script will create a pull request.
- If the `fbc.version_promotion_strategy` is set to `review-needed`, a one PR per operator
will be created and operator owners will be asked for an approval.
- If the `fbc.version_promotion_strategy` is set to `always`, a signle PR will be created
for all operators with the same strategy and PR will be released automatically.
- If the `fbc.version_promotion_strategy` is set to `never`, no PR will be created and
the operator will not be promoted to the next version.

## Usage

Pull the latest git repository of operator-pipelines
```bash
git clone git@github.com:redhat-openshift-ecosystem/operator-pipelines.git
cd operator-pipelines
```

The script is available in `scripts/promote-catalog.py`. Before running the script
export `GITHUB_TOKEN` environment variable with a token that has access to the repository.
```bash
export GITHUB_TOKEN=<token>
```

And then run the script. Always use the `--dry-run` option first to see what will be done.
```bash
python scripts/promote-catalog.py \
    --local-repo /tmp/community-operators-pipeline-preprod \
    --target-version 4.19 \
    --verbose --dry-run
```
