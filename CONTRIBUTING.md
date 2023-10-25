# Contributing Guide

All changes contributed to the code are validated by GitHub CI. To ensure
passing Ci workflow, the validation tests can also be run locally.

To prepare the local testing environment, follow one of the guides below.

## Testing setup on RPM-based Linux systems

Run the following commands:

```bash
sudo dnf -y install hadolint
python3 -m pip install pdm
pdm install
source .venv/bin/activate
python3 -m pip install ansible-lint tox-pdm
```

## Testing setup on other Linux systems

Before starting, make sure you have installed the [Brew][1] package manager.

```bash
brew install hadolint
python3 -m pip install pdm
pdm install
source .venv/bin/activate
python3 -m pip install ansible-lint tox-pdm
```

## Running tests

Simply run this command:

```bash
tox
```

[1]: https://brew.sh/