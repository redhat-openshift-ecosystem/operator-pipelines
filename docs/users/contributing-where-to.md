# Where to contribute

Once you have forked the upstream repo, you will require to add your Operator Bundle to the forked repo. The forked repo will have directory structure similar to the structure outlined below.

```bash
├── config.yaml
├── operators
│   └── new-operator
│       ├── 0.0.102
│       │   ├── manifests
│       │   │   ├── new-operator.clusterserviceversion.yaml
│       │   │   ├── new-operator-controller-manager-metrics-service_v1_service.yaml
│       │   │   ├── new-operator-manager-config_v1_configmap.yaml
│       │   │   ├── new-operator-metrics-reader_rbac.authorization.k8s.io_v1_clusterrole.yaml
│       │   │   └── tools.opdev.io_demoresources.yaml
│       │   ├── metadata
│       │   │   └── annotations.yaml
│       │   ├── release-config.yaml
│       │   └── tests
│       │       └── scorecard
│       │           └── config.yaml
│       ├── catalog-templates
│       │   ├── v4.14.yaml
│       │   ├── v4.15.yaml
│       │   └── v4.16.yaml
│       ├── ci.yaml
│       └── Makefile
└── README.md
```

Follow the `operators` directory in the forked repo. Add your Operator Bundle under this `operators` directory following the example format.

1. Under the `operators` directory, create a new directory with the name of your operator.
2. Inside of this newly created directory add your `ci.yaml` and set its content based on [doc](./operator-ci-yaml.md).
3. Also, under the new directory create a subdirectory for each version of your Operator.
4. In each version directory there should be a `manifests/` directory containing your OpenShift yaml files, a `metadata/` directory containing your `annotations.yaml` file, and a `tests/` directory containing the required `config.yaml` file for the preflight tests.
5. Create a `catalog-templates/` directory under the operator directory and add a yaml file for each OpenShift version you want to support. The yaml file should contain the catalog template for the operator. More information on how to create the catalog template can be found [here](./fbc_workflow.md).
6. Download the template `Makefile` from [here](https://raw.githubusercontent.com/redhat-openshift-ecosystem/operator-pipelines/main/fbc/Makefile) and place it in the root of the operator directory.

>**Note** To learn more about preflight tests please follow this [link](https://github.com/redhat-openshift-ecosystem/openshift-preflight?tab=readme-ov-file#preflight).

For partners and ISVs, certified operators can now be submitted via connect.redhat.com. If you have submitted your Operator there already, please ensure your submission here uses a different package name (refer to the README for more details).
