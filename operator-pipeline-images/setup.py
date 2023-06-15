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
            "verify-pr-title=operatorcert.entrypoints.verify_pr_title:main",
            "verify-pr-uniqueness=operatorcert.entrypoints.verify_pr_uniqueness:main",
            "verify-pr-user=operatorcert.entrypoints.verify_pr_user:main",
            "upload-artifacts=operatorcert.entrypoints.upload_artifacts:main",
            "download-test-results=operatorcert.entrypoints.download_test_results:main",
            "reserve-operator-name=operatorcert.entrypoints.reserve_operator_name:main",
            "set-github-status=operatorcert.entrypoints.set_github_status:main",
            "link-pull-request=operatorcert.entrypoints.link_pull_request:main",
            "get-cert-project-related-data=operatorcert.entrypoints.get_cert_project_related_data:main",
            "get-vendor-related-data=operatorcert.entrypoints.get_vendor_related_data:main",
            "open-pull-request=operatorcert.entrypoints.github_pr:main",
            "publish=operatorcert.entrypoints.publish:main",
            "index=operatorcert.entrypoints.index:main",
            "update-cert-project-status=operatorcert.entrypoints.update_cert_project_status:main",
            "hydra-checklist=operatorcert.entrypoints.hydra_checklist:main",
            "create-container-image=operatorcert.entrypoints.create_container_image:main",
            "pipelinerun-summary=operatorcert.entrypoints.pipelinerun_summary:main",
            "request-signature=operatorcert.entrypoints.request_signature:main",
            "upload-signature=operatorcert.entrypoints.upload_signature:main",
            "github-add-comment=operatorcert.entrypoints.github_add_comment:main",
            "set-cert-project-repository=operatorcert.entrypoints.set_cert_project_repository:main",
        ],
    },
)
