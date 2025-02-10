# Operator Publishing / Review settings

Each operator might have `ci.yaml` configuration file to be present in an operator directory (for example `operators/aqua/ci.yaml`). This configuration file is used by the pipeline automation to control a way how the operator will be published and reviewed.

A content of the file depends on the operator source type. There are a different set of options for community operators and certified operators.


> **Note:**
    One can create or modify `ci.yaml` file with a new operator version. This operation can be done in the same PR with other operator changes.

## Reviewers

> **Note:**
    This option is only valid for community operators. The certified or marketplace reviewer are configure using Red Hat Connect.

If you want to accelerate publishing your changes, consider adding yourself and others you trust to the `reviewers` list. If the author of PR will be in that list, changes she/he made will be taken as authorized changes. This will be the indicator for our pipeline that the PR is ready to merge automatically.

> **Note:**
    If an author of PR is not in `reviewers` list or not in `ci.yaml` on `main` branch, PR will not be merged automatically.

> **Note:**
    If an author of PR is not in `reviewers` list and `reviewers` are present in `ci.yaml` file. All `reviewers` will be mentioned in PR comment to check for upcoming changes.

For this to work, it is required to setup reviewers in `ci.yaml` file. It can be done by adding `reviewers` tag with a list of GitHub usernames. For example

### Example
```yaml
$ cat <path-to-operator>/ci.yaml
---
reviewers:
  - user1
  - user2

```

## FBC mode

### `fbc.enabled`
The `fbc.enabled` flag enables the [File-Based catalog](./fbc_workflow.md) feature. It is highly recommended to use the FBC mode in order to have better control over the operator's catalog.

### `fbc.version_promotion_strategy`
The `fbc.version_promotion_strategy` option defines the strategy for promoting the operator into a next OCP version. When a new OCP version becomes available an automated process will promote the operator from a version N to a version N+1. The `fbc.version_promotion_strategy` option can have the following values:

- `never` - the operator will not be promoted to the next OCP version automatically (default)
- `always` - the operator will be promoted to the next OCP version automatically
- `review-needed` - the operator will be promoted to the next OCP version automatically, but the PR will be created and the reviewers will be asked to review the changes

### `fbc.catalog_mapping`
The mapping serves as a link between catalog templates within the `./catalog-templates` directory and catalogs within the `./catalogs` directory.

For more details and structure visit the [FBC workflow page](./fbc_workflow.md#fbc-template-mapping).

### Example
```yaml
---
fbc:
  enabled: true
  version_promotion_strategy: never
  catalog_mapping:
    - template_name: my-custom-semver-template.yaml # The name of the file inside ./catalog-templates directory
        catalogs_names: # a list of catalogs within the /catalogs directory
          - "v4.15"
          - "v4.16"
          - "v4.17"
        type: olm.semver
    - template_name: my-custom-basic-template.yaml # The name of the file inside catalog-templates directory
        catalogs_names:
          - "v4.12"
          - "v4.13"
        type: olm.template.basic
```


## Operator versioning
> **_NOTE:_** This option is only available for the non-FBC operators where user doesn't have a direct control over the catalog.

Operators have multiple versions. When a new version is released, OLM can update an operator automatically. There are 2 update strategies possible, which are defined in `ci.yaml` at the operator top level.

### replaces-mode
Every next version defines which version will be replaced using `replaces` key in the CSV file. It means, that there is a possibility to omit some versions from the *update graph*. The best practice is to put them in a separate channel then.

### semver-mode
Every version will be replaced by the next higher version according to semantic versioning.

### Restrictions
A contributor can decide if `semver-mode` or `replaces-mode` mode will be used for a specific operator. By default, `replaces-mode` is activated, when `ci.yaml` file is present and contains `updateGraph: replaces-mode`. When a contributor decides to switch and use `semver-mode`, it will be specified in `ci.yaml` file or the key `updateGraph` will be missing.

### Example
```
$ cat <path-to-operator>/ci.yaml
---
# Use `replaces-mode` or `semver-mode`.
updateGraph: replaces-mode
```

## Certification project

### `cert_project_id`
The `cert_project_id` option is required for certified and marketplace operators. It is used to link the operator to the certification project in Red Hat Connect.

## Kubernetes max version in CSV

Starting from kubernetes 1.22 some old APIs were deprecated ([Deprecated API Migration Guide from v1.22](https://kubernetes.io/docs/reference/using-api/deprecation-guide/#v1-22). Users can set `operatorhub.io/ui-metadata-max-k8s-version: "<version>"` in its CSV file to inform its maximum supported Kubernetes version. The following example will inform that operator can handle `1.21` as maximum Kubernetes version
```
$ cat <path-to-operators>/<name>/<version>/.../my.clusterserviceversion.yaml
metadata:
  annotations:
    operatorhub.io/ui-metadata-max-k8s-version: "1.21"
```
