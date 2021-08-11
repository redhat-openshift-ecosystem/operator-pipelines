import pathlib
from setuptools import setup, find_packages

here = pathlib.Path(__file__).resolve().parent

with open(here.joinpath("requirements.txt")) as fh:
    req = fh.readlines()

with open(here.joinpath("requirements-dev.txt")) as fh:
    req_dev = fh.readlines()


setup(
    name="operatorcert",
    version="1.0.0",
    description="Tools for Red Hat Operator certification pipelines",
    author="Red Hat, Inc.",
    packages=find_packages(),
    python_requires=">=3.6, <4",
    install_requires=req,
    extras_require={"dev": req_dev},
    entry_points={
        "console_scripts": [
            "bundle-dockerfile=operatorcert.entrypoints.bundle_dockerfile:main",
            "ocp-version-info=operatorcert.entrypoints.ocp_version_info:main",
            "verify-changed-dirs=operatorcert.entrypoints.verify_changed_dirs:main",
            "verify-submission=operatorcert.entrypoints.verify_submission:main",
            "upload-artifacts=operatorcert.entrypoints.upload_artifacts:main",
            "reserve-operator-name=operatorcert.entrypoints.reserve_operator_name:main",
        ],
    },
)
