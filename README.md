# operator-pipelines-images
Container images containing the set of tools for Partner Operator Bundle [certification pipelines](https://github.com/redhat-openshift-ecosystem/operator-pipelines).

## Development

To install the python package in a development environment, run:

```bash
pip install ".[dev]"
```

To test the scripts with the pipelines, see [local-dev.md](docs/local-dev.md).

To run unit tests and code style checkers:

```bash
tox
```