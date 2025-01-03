# Catalog image browser
Working with catalog images locally might be a tricky task since it requires a lot of manual work.
To make it easier for maintainers and contributors, we have created a simple catalog image
browser CLI tool that allows you to browse and search for images in the catalog locally
in your terminal.

## Installation
To install the catalog browser, you will need a Python 3.10+ environment.

Then, you can install the tool using pip:

```bash
$ pip install git+https://github.com/redhat-openshift-ecosystem/operator-pipelines.git
```

Once installed you can run the tool using the following command:

```bash
$ catalog-browser --help

usage: catalog-browser [-h] [--image IMAGE] [--rendered RENDERED] {list,show} ...

Browse and query index image content.

positional arguments:
  {list,show}          Commands
    list               List content in the index image.
    show               Show details of specific content.

options:
  -h, --help           show this help message and exit
  --image IMAGE        Path to the index image.
  --rendered RENDERED  Path to the rendered index image content.

```

## Usage
The browser requires one of 2 argument inputs: `--image` or `--rendered`. Using `--image` argument
the tool will pull the image and extract the content to a temporary directory. Based on catalog image
size the extraction might take a while. You can also render a catalog
in advance using `opm render` and then using `--rendered` argument to browse the content.

```bash
$ catalog-browser --image registry.redhat.io/redhat/community-operator-index:v4.16 list packages

# or
$ opm render -o yaml registry.redhat.io/redhat/community-operator-index:v4.16 > /tmp/v.4.16.yaml

$ catalog-browser --rendered /tmp/v.4.16.yaml list bundles
```

The browser supports 2 commands: `list` and `show`.

### List
The `list` command will list all packages, bundles or channels
```bash
$ catalog-browser --image registry.redhat.io/redhat/community-operator-index:v4.16 list packages
3scale-community-operator
ack-acm-controller
ack-acmpca-controller
ack-apigateway-controller
ack-apigatewayv2-controller
ack-applicationautoscaling-controller
ack-athena-controller
...
```

```bash
$ catalog-browser --rendered /tmp/v.4.16.yaml list bundles
3scale-community-operator.v0.10.1
3scale-community-operator.v0.8.2
3scale-community-operator.v0.9.0
ack-acm-controller.v0.0.1
ack-acm-controller.v0.0.10
ack-acm-controller.v0.0.12
ack-acm-controller.v0.0.16
ack-acm-controller.v0.0.17
ack-acm-controller.v0.0.18
...
```

### Show
The `show` command will show details of a specific package, bundle or channel in
human readable format.

To show details of a package:
```bash
$ catalog-browser --rendered /tmp/v.4.16.yaml show package tempo-operator
Package: tempo-operator
Channels:
 - tempo-operator/alpha
Bundles:
 - tempo-operator.v0.1.0
 - tempo-operator.v0.10.0
 - tempo-operator.v0.11.0
 - tempo-operator.v0.11.1
 - tempo-operator.v0.12.0
 - tempo-operator.v0.13.0
 - tempo-operator.v0.14.0
 - tempo-operator.v0.14.1
 - tempo-operator.v0.14.2
 - tempo-operator.v0.2.0
 - tempo-operator.v0.3.0
 - tempo-operator.v0.4.0
 - tempo-operator.v0.5.0
 - tempo-operator.v0.6.0
 - tempo-operator.v0.7.0
 - tempo-operator.v0.8.0
 - tempo-operator.v0.9.0
```

To show details of a bundle:
```bash
$ catalog-browser --rendered /tmp/v.4.16.yaml show bundle snyk-operator.v1.90.2
Bundle: snyk-operator.v1.90.2
Package: snyk-operator
Image: quay.io/openshift-community-operators/snyk-operator@sha256:daf143ff1e9fbcf9bbbb350f8aab8593a1a35f693b0118c06a6b84c89a474397
Channels:
 - snyk-operator/stable
```
