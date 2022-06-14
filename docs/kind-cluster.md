# KIND Cluster Setup

The testing pipeline for community operators is running in local kind cluster with own local registry and its dependencies like OLM, Tekton and others. The following steps must be performed
to prepare the kind clusters for use by the pipeline. 

## Prerequisites
The KIND Cluster Setup is done by `ansible`. One can install `ansible` via 
```
$ pip3 install ansible
```
Then one has to install additional `ansible` collection `kubernetes.core` and its dependency python `kubernetes` package
```
$ pip3 install kubernetes
$ ansible-galaxy collection install kubernetes.core
```

## Kind Cluster Instllation

### Install
```
$ ansible-pull ansible/playbooks/upstream-community.yaml \
  -U https://github.com/redhat-openshift-ecosystem/operator-pipelines.git \
  -C main  \
  -i localhost, \
  -e prerequisites=true \ 
  -e kind_cluster=true \
  --tags install
```

### Verify installation
```
$ ansible-pull ansible/playbooks/upstream-community.yaml \
  -U https://github.com/redhat-openshift-ecosystem/operator-pipelines.git \
  -C main  \
  -i localhost, \
  -e prerequisites=true \ 
  -e kind_cluster=true \
  --tags verify 
```

### Cleanup kind cluster

```
$ ansible-pull ansible/playbooks/upstream-community.yaml \
  -U https://github.com/redhat-openshift-ecosystem/operator-pipelines.git \
  -C main  \
  -i localhost, \
  -e prerequisites=false \
  -e kind_cluster=true \
  --tags clean 
```

### Uninstall everything (prerequisites and Kind cluster)
```
$ ansible-pull ansible/playbooks/upstream-community.yaml \
  -U https://github.com/redhat-openshift-ecosystem/operator-pipelines.git \
  -C main  \
  -i localhost, \
  -e prerequisites=true \
  -e kind_cluster=true \
  --tags clean 
```

### Destroy KIND cluster

```
$ ansible-pull ansible/playbooks/upstream-community.yaml \
  -U https://github.com/redhat-openshift-ecosystem/operator-pipelines.git \
  -C main  \
  -i localhost, \
  --tags kind-delete
```

### Upgrade prerequisites/tools installation
```
$ ansible-pull ansible/playbooks/upstream-community.yaml \
  -U https://github.com/redhat-openshift-ecosystem/operator-pipelines.git \
  -C main  \
  -i localhost, \
  -e prerequisites=true \ 
  -e kind_cluster=false \
  --tags install
```

## Operator pipeline tekton tasks and pipelines

```
$ ansible-pull ansible/playbooks/upstream-community.yaml \
  -U https://github.com/redhat-openshift-ecosystem/operator-pipelines.git \
  -C main  \
  -i localhost, \
  --tags tekton-task,tekton-pipeline
```

