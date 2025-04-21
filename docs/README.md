# Openshift Operators

## About this repository

This repo is the canonical source for Kubernetes Operators that appear on [OpenShift Container Platform](https://openshift.com) and [OKD](https://www.okd.io/).

**NOTE** The index catalogs:

- `registry.redhat.io/redhat/certified-operator-index:v<OCP Version>`
- `registry.redhat.io/redhat/redhat-marketplace-index:v<OCP Version>`
- `registry.redhat.io/redhat/community-operator-index:v<OCP Version>`

are built from this repository and it is
consumed by Openshift and OKD to create their sources and built their catalog. To know more about how
Openshift catalog are built see the [documentation](https://docs.openshift.com/container-platform/4.14/operators/understanding/olm-rh-catalogs.html#olm-rh-catalogs_olm-rh-catalogs).

See our [documentation](https://redhat-openshift-ecosystem.github.io/operator-pipelines/) to find out
more about Community, Certified and Marketplace operators and contribution.

## Add your Operator

We would love to see your Operator added to this collection. We currently use automated vetting via continuous integration plus manual review to curate a list of high-quality, well-documented Operators. If you are new to Kubernetes Operators start [here](https://sdk.operatorframework.io/build/).

If you have an existing Operator read our contribution guidelines on how to [open a PR](users/contributing-via-pr.md). Then the community operator pipeline will be triggered to test your Operator and merge a Pull Request.

## Remove Your Operator

**Before You Begin**
Ensure your operator follows the [FBC (File-Based Catalog)](users/fbc_onboarding.md#file-based-catalog-onboarding) workflow.  
Setting fbc.enabled: true in the ci.yaml file is not enough. The operator must be fully onboarded to FBC.  
For non-FBC (bundle-based) operators, refer to the [FBC onboarding guide](users/fbc_onboarding.md#convert-existing-operator-to-fbc) before continuing.

Depending on your use case, you may:
- [Remove the operator entirely from all catalogs.](#remove-the-entire-operator-from-the-catalog)
- [Remove it from specific catalog version(s).](#remove-the-operator-from-specific-catalog-versions)
- [Remove a single operator version from the catalog.](#remove-a-single-operator-bundle-version)

### Remove the Entire Operator from the Catalog

To remove the operator completely from the catalog:

- Delete the your operator directory from the `operators/` folder.
- Remove all catalog files related to your operator from the `catalogs/` directory.
- Open a **single** pull request that includes these changes. Follow our contribution guidelines on how to [open a PR](users/contributing-via-pr.md).

For reference, here’s an [example PR](https://github.com/redhat-openshift-ecosystem/community-operators-prod/pull/5955/files) demonstrating these steps.

### Remove the Operator from Specific Catalog Version(s)

To remove your operator from selected catalog versions:

- In the `catalogs/` directory, delete the your operator related catalog file from the targeted catalog version(s).
- In `operators/<operator-name>/ci.yaml`, locate the `fbc.catalog_mapping` section and remove the targeted catalog version(s) from the `catalog_names` list.

Example:

```yaml
fbc:
  enabled: true
  catalog_mapping:
    - template_name: basic.yaml
      catalog_names: ["v4.14", "v4.15", "v4.16"]
      type: olm.template.basic
```
To remove `v4.15`, update `catalog_names` to:

```yaml
catalog_names: ["v4.14", "v4.16"]
```
- From the `operators/<operator-name>/catalog-templates/` directory, delete any template YAML files that were associated with the removed catalog version(s), if applicable.
- Submit a single pull request with all these changes. Follow our [PR guidelines](users/contributing-via-pr.md).

### Remove a Single Operator Bundle Version

To remove a specific operator bundle version without affecting other versions:

- Identify all catalog files under the catalog/ directory for each catalog version where the targeted operator version is present. These files are typically located at `catalogs/<catalog_version>/<your_operator>/catalog.yaml`. Modify each of these catalog version files and remove the targeted operator version's bundle details from your operator's subdirectory.
- Remove the entire targeted operator bundle version subdirectory located at `operators/<your_operator_name>/`.
- Remove the targeted operator version from the list of catalog-templates files located at `operators/<your_operator>/catalog-templates/`.
- Submit a single pull request that includes this change.

For reference, see this [example pull request](https://github.com/Allda/community-operators-pipeline-preprod/pull/34/files).

## Contributing Guide

- [Prerequisites](users/contributing-prerequisites.md)
- [Where to place operator](users/contributing-where-to.md)
- [Creating pull request (PR)](users/contributing-via-pr.md)
- [Operator Publishing / Review settings](users/operator-ci-yaml.md)
- [OKD/OpenShift Catalogs criteria and options](users/packaging-required-criteria-ocp.md)

## Test and release process for the Operator

Refer to the [operator pipeline documentation](users/pipelines_overview.md) .

## IMPORTANT NOTICE

Some APIs versions are deprecated and are OR will no longer be served on the Kubernetes version
`1.22/1.25/1.26` and consequently on vendors like Openshift `4.9/4.12/4.13`.

**What does it mean for you?**

Operator bundle versions using the removed APIs can not work successfully from the respective releases.
Therefore, it is recommended to check if your solutions are failing in these scenarios to stop using these versions
OR by setting the `"olm.properties": '[{"type": "olm.maxOpenShiftVersion", "value": "<OCP version>"}]'`
to block cluster admins upgrades when they have Operator versions installed that can **not**
work well in OCP versions higher than the value informed. Also, by defining a valid OCP range via the annotation `com.redhat.openshift.versions`
into the `metadata/annotations.yaml` for our solution does **not** end up shipped on OCP/OKD versions where it cannot be installed.

> WARNING: `olm.maxOpenShiftVersion` should ONLY be used if you are 100% sure that your Operator bundle version
> cannot work in upper releases. Otherwise, you might provide a bad user experience. Be aware that cluster admins
> will be unable to upgrade their clusters with your solution installed. Then, suppose you do not provide any upper
> version and a valid upgrade path for those who have your Operator installed be able to upgrade it and consequently
> be allowed to upgrade their cluster version (i.e from OCP 4.10 to 4.11). In that case, cluster admins might
> choose to uninstall your Operator and no longer use it so that they can move forward and upgrade their cluster
> version without it.

Please, make sure you check the following announcements:
- [How to deal with removal of v1beta1 CRD removals in Kubernetes 1.22 / OpenShift 4.9](https://github.com/redhat-openshift-ecosystem/community-operators-prod/discussions/138)
- [Kubernetes API removals on 1.25/1.26 and Openshift 4.12/4.13 might impact your Operator. How to deal with it?](https://github.com/redhat-openshift-ecosystem/community-operators-prod/discussions/1182)

## Reporting Bugs

Use the issue tracker in this repository to report bugs.

[k8s-deprecated-guide]: https://kubernetes.io/docs/reference/using-api/deprecation-guide/#v1-22
