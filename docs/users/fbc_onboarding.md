# File Based Catalog onboarding

> **Note**: The File Based Catalog support is now in an alpha phase. We welcome any feedback you have for this new feature.

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
As a prerequisite to this process, you need to download a `Makefile` that
automates the migration process.

```bash
# Go to the operator repo directory (certified-operators, marketplace-operators, community-operators-prod)
cd <operator-repo>/operator/<operator-name>
wget https://raw.githubusercontent.com/redhat-openshift-ecosystem/operator-pipelines/main/fbc/Makefile
```

Now we can convert existing operator into FBC. The initial run takes a while because
a local cache is generated during a run.

> [!NOTE]
> A user executing the conversion script needs to be authenticated to registries used by OLM catalog.
> Use `podman login` to log in into all registries.

To convert existing operator to `FBC` format you need to execute following command:

```bash
$ make fbc-onboarding

2024-04-24 15:53:05,537 [operator-cert] INFO Generating FBC templates for the following versions: ['4.12', '4.13', '4.14', '4.15', '4.16']
2024-04-24 15:53:07,632 [operator-cert] INFO Processing catalog: v4.12
2024-04-24 15:53:07,633 [operator-cert] DEBUG Building cache for registry.stage.redhat.io/redhat/community-operator-index:v4.12
...
```

> [!IMPORTANT]
> In case an operator isn't shipped to all OCP catalog versions manually update `OCP_VERSIONS`
> variable in the `Makefile` and include only versions supported by an operator.

The Makefile will execute following steps:
 - Download dependencies needed for the migration (opm, fbc-onboarding CLI)
 - Fetch a list of currently supported OCP catalogs (this might take a while when doing it for the first time)
 - Transform existing catalogs into a basic template
 - Generate an FBC catalog for a given operator
 - Update operator ci.yaml config

After a script is finished you should see a template and generated fbc in the repository.
```bash
$ tree operators/aqua

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
make catalog
```

Of course, you can choose any type of template that you prefer by modifying the Makefile target.
More information about catalog templates can be found [here](https://olm.operatorframework.io/docs/reference/catalog-templates/)
