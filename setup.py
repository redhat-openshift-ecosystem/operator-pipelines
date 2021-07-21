from setuptools import setup, find_packages

setup(
    name="operatorcert",
    version="1.0.0",
    description="Tools for Red Hat Operator certification pipelines",
    author="Red Hat, Inc.",
    packages=find_packages(),
    python_requires=">=3.6, <4",
    install_requires=[
        "pyyaml==5.4.1",
        "requests==2.26.0",
        "yq==2.12.2",
    ],
    extras_require={
        "dev": [
            "black",
            "pytest",
            "pytest-cov",
        ],
    },
    entry_points={
        "console_scripts": [
            "bundle-dockerfile=operatorcert.entrypoints.bundle_dockerfile:main",
            "ocp-version-info=operatorcert.entrypoints.ocp_version_info:main",
        ],
    },
)
