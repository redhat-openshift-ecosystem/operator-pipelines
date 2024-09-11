# Developer Guide

## Workflow

1. [Run through the setup](#setup) at least once.
1. [Make changes to the pipeline image](#making-changes-to-the-pipeline-image),
   if desired.
1. [Make changes to the Tekton pipelines and/or tasks](#making-changes-to-the-pipelines),
   if desired.
1. [Test all impacted pipelines](../README.md#usage).
   - [Override the pipeline image as necessary](../README.md#using-a-custom-pipeline-image).
1. Submit a pull request with your changes.

## Setup

1. [Git leaks detection](#git-leaks-detection)
1. [Prepare a development environment](#prepare-a-development-environment)
1. [Prepare a certification project](#prepare-a-certification-project)
1. [Prepare an Operator bundle](#prepare-an-operator-bundle)
1. [Prepare your `ci.yaml`](#prepare-your-ciyaml)
1. [Create a bundle pull request](#create-a-bundle-pull-request) (optional)
   - Required for testing hosted or release pipelines
1. [Create an API key](#create-an-api-key) (optional)
   - Required for testing submission with the CI pipeline
1. [Prepare the CI to run from your fork](ci-cd.md) (optional)
   - Required to run integration testing on forks of this repo.

### Git leaks detection

Since the repository contains secret information in form of encrypted
Ansible Vault there is high chance that developer may push a commit with
decrypted secrets by mistake. To avoid this problem we recommend
to use `Gitleaks` tool that prevent you from commit secret code into git history.

The repository is already pre-configured but each developer has to make final
config changes in his/her environment.

Follow the [documentation](https://github.com/gitleaks/gitleaks#pre-commit) to
configure Gitleaks on your computer.

### Prepare a Development Environment

You may use any OpenShift 4.7+ cluster (including [CodeReady Containers](#using-codeready-containers)).

The hosted and release pipelines require a considerable amount of dependencies which
are tedious to [configure manually](pipeline-env-setup.md). Luckily these
steps have been automated and can be executed by anyone with access to the Ansible
vault password.

Before running this you should ensure you're logged into the correct OpenShift
cluster using `oc`. If already logged into the OpenShift console, an `oc` login
command can be obtained by clicking on your username in upper right corner, and
selecting `copy login command`.

```bash
ansible-playbook -v \
  -i "ansible/inventory/operator-pipeline-$ENV" \
  -e "oc_namespace=$NAMESPACE" \
  -e "ocp_token=`oc whoami -t`" \
  --vault-password-file $VAULT_PASSWORD_PATH \
  ansible/playbooks/deploy.yml
```

:warning: Conflicts may occur if the project already contains some resources.
They may need to be removed first.

Cleanup can be performed by specifying the `absent` state for some of the resources.

```bash
ansible-playbook -v \
  -i "ansible/inventory/operator-pipeline-$ENV" \
  -e "oc_namespace=$NAMESPACE" \
  -e "ocp_token=`oc whoami -t`" \
  -e "namespace_state=absent" \
  -e "github_webhook_state=absent" \
  --vault-password-file $VAULT_PASSWORD_PATH \
  ansible/playbooks/deploy.yml
```

#### Integration tests

See [integration tests section in ci-cd.md](ci-cd.md#integration-tests)

#### Install tkn

You should install the [tkn](https://docs.openshift.com/container-platform/4.7/cli_reference/tkn_cli/installing-tkn.html)
CLI which corresponds to the version of the cluster you're utilizing.

#### Using CodeReady Containers

It's possible to deploy and test the pipelines from a CodeReady Containers (CRC)
cluster for development/testing, purposes.

1. Install [CodeReady Containers](https://code-ready.github.io/crc/#installation_gsg)

1. Install [OpenShift Pipelines](https://docs.openshift.com/container-platform/4.7/cicd/pipelines/installing-pipelines.html)

1. Login to your cluster with `oc` CLI.

    You can run `crc console --credentials` to get the admin login command.

1. Create a test project in your cluster

    ```bash
    oc new-project playground
    ```

1. Grant the `privileged` SCC to the default `pipeline` service account.

    The `buildah` task requires the `privileged` security context constraint
    in order to call `newuidmap`/`newgidmap`. This is only necessary because
    `runAsUser:0` is defined in `templates/crc-pod-template.yml`.

    ```bash
    oc adm policy add-scc-to-user privileged -z pipeline
    ```

##### Running a Pipeline with CRC

It may be necessary to pass the following `tkn` CLI arg to avoid
permission issues with the default CRC PersistentVolumes.

```bash
--pod-template templates/crc-pod-template.yml
```

#### Prepare a Certification Project

A certification project is required for executing all pipelines.
In order to avoid collisions with other developers, it's best to
create a new one in the corresponding Pyxis environment.

The pipelines depend on the following certification project fields:

```jsonc
{
  "project_status": "active",
  "type": "Containers",

  // Arbitrary name for the project - can be almost anything
  "name": "<insert-project-name>",

  /*
   Either "connect", "marketplace" or "undistributed".
   This maps to the `organization` field in the bundle submission repo's config.yaml.
     connect -> certified-operators
     marketplace -> redhat-marketplace
     undistributed -> certified-operators (certified against, but not distributed to)
  */
  "operator_distribution": "<insert-distribution>",

  // Must correspond to a containerVendor record with the same org_id value.
  "org_id": <insert-org-id>,

  "container": {
    "type": "operator bundle image",

    "build_catagories":"Operator bundle",

    // Required but always "rhcc"
    "distribution_method": "rhcc",

    // Always set to true to satisfy the publishing checklist
    "distribution_approval": true,

    // Must match the github user(s) which opened the test pull requests
    "github_usernames": ["<insert-github-username>"],

    // Must be unique for the vendor
    "repository_name": "<insert-repo-name>"
  }
}
```

#### Prepare an Operator Bundle

You can use a utility script to copy an existing bundle. By default it will copy
a bundle that should avoid common failure conditions such as digest pinning.
View all the customization options by passing `-h` to this command.

```bash
./scripts/copy-bundle.sh
```

You may wish to tweak the generated output to influence the behavior of the pipelines.
For example, Red Hat Marketplace Operator bundles may require additional annotations.
The pipeline should provide sufficient error messages to indicate what is missing.
If such errors are unclear, that is likely a bug which should be fixed.

#### Prepare Your ci.yaml

At the root of your operator package directory (note: **not** the bundle
version directory) there needs to be a `ci.yaml` file. For development
purposes, it should follow this format in most cases.

```yaml
---
# Copy this value from the _id field of the certification project in Pyxis.
cert_project_id: <pyxis-cert-project-id>
# Set this to true to allow the hosted pipeline to merge pull requests.
merge: false
```

#### Create a Bundle Pull Request

It's recommended to open bundle pull requests against the
[operator-pipelines-test](https://github.com/redhat-openshift-ecosystem/operator-pipelines-test)
repo. The pipeline GitHub bot account has permissions to manage it.

> **Note:** This repository is only configured for testing certified operators,
> NOT Red Hat Marketplace operators (see
> [`config.yaml`](https://github.com/redhat-openshift-ecosystem/operator-pipelines-test/blob/main/config.yaml)).

```bash
# Checkout the pipelines test repo
git clone https://github.com/redhat-openshift-ecosystem/operator-pipelines-test
cd operator-pipelines-test

# Create a new branch
git checkout -b <insert-branch-name>

# Copy your package directory
cp -R <package-dir>/ operators/

# Commit changes
git add -A

# Use this commit pattern so it defaults to the pull request title.
# This is critical to the success of the pipelines.
git commit -m "operator <operator-package-name> (<bundle-version>)"

# Push your branch. Open the pull request using the output.
git push origin <insert-branch-name>
```

> **Note:** You may need to merge the pull request to use it for testing
> the release pipeline.

#### Create an API Key

[File a ticket](https://url.corp.redhat.com/86973d1) with Pyxis admins
to assist with this request. It must correspond to the `org_id`
for the certification project under test.

## Making Changes to the Pipelines

### Guiding Principles

- Avoid including credentials within Task scripts.
  - Avoid the use of `set -x` in shell scripts which _could_ expose credentials
    to the console.
- Don't use workspaces for passing secrets. Use `secretKeyRef` and `volumeMount`
  with secret and key names instead.
  - Reason: It adds unnecessary complexity to `tkn` commands.
- Use images from trusted registries/namespaces.
  - registry.redhat.io
  - registry.access.redhat.com
  - quay.io/redhat-isv
  - quay.io/opdev
- Use image pull specs with digests instead of tags wherever possible.
- Tasks must implement their own skipping behavior, if needed.
  - Reason: If a task is not executed, any dependent tasks will not be
    executed either.
- Don't use ClusterTasks or upstream tasks. All tasks are defined in this repo.
- Document all params, especially pipeline params.
- Output human readable logs.
- Use reasonable defaults for params wherever possible.

### Applying Pipeline Changes

You can use the following command to apply all local changes to your OCP project.
It will add all the Tekton resources used across all the pipelines.

```bash
oc apply -R -f ansible/roles/operator-pipeline/templates/openshift
```

## Making Changes to the Pipeline Image

### Dependency

Operator pipelines project is configured to automatically manage Python
dependencies using [PDM][1] tool. The pdm automates definition, installation,
upgrades and the whole lifecycle of dependency in a project. All dependencies
are stored in `pyproject.toml` file in a groups that corresponds to individual
applications within the Operator pipelines project.

Adding, removing and updating of dependency needs to be always done
using `pdm` cli.

```bash
pdm add -G operator-pipelines gunicorn==20.1.0
```

After a dependency is installed it is added to pdm.lock file. The lock file
is always part of git repository.

If you want to install specific group set of dependencies use following command:

```bash
pdm install -G operator-pipelines
```

Dependencies are stored into virtual environment (.venv) which is automatically
created after `pdm install`. If .venv wasn't created, configure pdm to
automatically create it during installation with `pdm config python.use_venv true`.

### Run Unit Tests, Code Style Checkers, etc.

Before running the tests locally, the environment needs to be prepared.
Choose the preparation process according to your Linux version.

#### Preparation on RPM-based Linux

```bash
sudo dnf -y install hadolint
python3 -m pip install pdm
pdm venv create 3.12
pdm install
source .venv/bin/activate
python3 -m pip install ansible-lint
```

#### Preparation on other Linux systems

Before starting, make sure you have installed the [Brew][2] package manager.

```bash
brew install hadolint
python3 -m pip install pdm
pdm venv create 3.12
pdm install
source .venv/bin/activate
python3 -m pip install ansible-lint
```

#### Run the local tests

To run unit tests and code style checkers:

```bash
tox
```

### Local development

Setup python virtual environment using pdm.

```shell
pdm venv create 3.12
pdm install
source .venv/bin/activate
```

### Build & Push

1. Ensure you have [buildah](https://github.com/containers/buildah/blob/main/install.md)
   installed

2. Build the image

    ```bash
    buildah bud
    ```

3. Push the image to a remote registry, eg. Quay.io.

    ```bash
    buildah push <image-digest-from-build-step> <remote-repository>
    ```

    This step may require login, eg.

    ```bash
    buildah login quay.io
    ```

[1]: https://pdm.fming.dev/latest/
[2]: https://brew.sh/
