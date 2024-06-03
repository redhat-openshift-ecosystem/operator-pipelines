# File Based Catalog onboarding

> **Note**: The FBC support is going to be released at the end of Q2 2024. Until that and until official announcement the steps below are not yet supported.

Operators in certified, marketplace, or community repositories are defined in a declarative way.
This means a user provides all necessary information in advance about the operator bundle and how it
should be released in a catalog and OPM automation injects a bundle into the correct place
in the upgrade path.

This is however very limited solution that doesn't allow any further modification of upgrade
paths after a bundle is already released. Due to this limitation, a concept
of FBC (File-based catalog) is now available and allows users to modify the operator upgrade
path in a separate step without the need to release a new bundle.

To enable FBC for a given operator the operator owner needs to convert
existing operator into FBC format.

We want to help with this process and we prepared a tooling that helps with this transition.

## Convert existing operator to FBC
As a prerequisite to this process, you need to install a few dependencies.

```bash
# Go to the operator repo directory (certified-operators, marketplace-operators, community-operators-prod)
cd certified-operators

# Install a migration script
pip install git+https://github.com/redhat-openshift-ecosystem/operator-pipelines.git

# Download opm cli tool
curl -sL https://github.com/operator-framework/operator-registry/releases/download/v1.39.0/linux-amd64-opm -o opm && \
chmod +x opm && mv opm ~/.local/bin
```

Now we can convert existing operator into FBC. The initial run takes a while because
a local cache is generated during a run.

The script will execute the following steps:
 - Fetch a list of currently supported OCP catalogs
 - Transform existing catalogs into a basic template
 - Generate FBC catalog contributions for an operator for all supported catalog versions
 - Update operator ci.yaml config

The following examples will be using `aqua` operator as an example. Change an operator name that matches the operator you want to convert.
```bash
$ fbc-onboarding --operator-name aqua \
 --repo-root . \
 --verbose

2024-04-24 15:53:05,537 [operator-cert] INFO Generating FBC templates for the following versions: ['4.12', '4.13', '4.14', '4.15', '4.16']
2024-04-24 15:53:07,632 [operator-cert] INFO Processing catalog: v4.12
2024-04-24 15:53:07,633 [operator-cert] DEBUG Building cache for registry.stage.redhat.io/redhat/community-operator-index:v4.12
...
```

After a script is finished you should see a template and generated fbc in the repository.
```bash
$ tree operatos/aqua

operators/aqua
├── 0.0.1
...
├── catalog-templates
│   ├── v4.12.yaml
│   ├── v4.13.yaml
│   ├── v4.14.yaml
│   ├── v4.15.yaml
│   └── v4.16.yaml
├── ci.yaml
```
... and File-based catalog in `catalogs` directory
```bash
$ tree (repository root)/catalogs
catalogs
├── v4.12
│   └── aqua
│       └── catalog.yaml
├── v4.13
│   └── aqua
│       └── catalog.yaml
├── v4.14
│   └── aqua
│       └── catalog.yaml
├── v4.15
│   └── aqua
│       └── catalog.yaml
└── v4.16
    └── aqua
        └── catalog.yaml

```

## Submit FBC changes
Artifacts generated in the previous step need to be added to a git and submitted via pull request. The operator pipeline validates the content of the catalogs and releases changes into ocp catalogs.

```bash
$ git add operators/aqua/{catalog-templates,ci.yaml}

$ git add catalogs/{v4.12,v4.13,v4.14,v4.15,v4.16}/aqua

$ git commit --signoff -m "Add FBC resources for aqua operator"
```

## Generating catalogs from templates
Catalog templates are used to simplify a view of a catalog and allow easier manipulation of catalogs. The automated conversion pre-generates a basic template that can be turned into full FBC using the following command:

```bash
opm alpha render-template basic ./catalog-templates/v${VERSION}.yaml > ${ROOT}/catalogs/v${VERSION}/${OPERATOR_NAME}/catalog.yaml
```
For the example `aqua` operator above, if could look like:
```bash
ROOT=../..
for VERSION in "4.12 4.13 4.14 4.15 4.16"
do
   opm alpha render-template basic ./catalog-templates/v${VERSION}.yaml > ${ROOT}/catalogs/v${VERSION}/aqua/catalog.yaml
done
```

# -------------------------------------------------------------------
## @Ales
not sure why the Makefile 'workflow' is separate from this doc, since the care-and-maintenance of catalog templates is pretty closely tied to an automation path, like the Makefile target:
```Makefile
# --- BASIC TEMPLATE ---
catalog: basic
```
I'd be tempted to merge these two docs and keep the "howto generate FBC contributions" is all about the Makefile,
deleting the contribution generation phases from the onboarding doc & script
# -------------------------------------------------------------------


Of course, you can choose any type of template that you prefer. More information about catalog templates can be found [here](https://olm.operatorframework.io/docs/reference/catalog-templates/)