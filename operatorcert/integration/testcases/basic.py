"""
Basic test cases
"""

import logging
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Optional

from git import Repo

from operatorcert.integration.config import Config
from operatorcert.integration.testcase import BaseTestCase, integration_test_case


@integration_test_case
class AddBundle(BaseTestCase):  # pragma: no cover
    """
    Test the addition of a non-FBC bundle
    """

    def __init__(self, config: Config, logger: logging.Logger) -> None:
        super().__init__(config, logger)
        self.tempdir: Optional[Path] = None

    def setup(self) -> None:
        self.tempdir = Path(mkdtemp(prefix=self.run_id + "-"))
        test_branch = "add-bundle"
        remote_branch = f"test-{self.run_id}"
        git_fixture_dir = self.tempdir / "git-fixture"
        # clone fixture repo locally
        local_repo = Repo.clone_from(
            self.config.fixtures_repository.url, git_fixture_dir, branch=test_branch
        )
        # configure remotes
        local_repo.create_remote("operators", url=self.config.operator_repository.url)
        local_repo.create_remote(
            "contributor", url=self.config.contributor_repository.url
        )
        # The fixture branch contains the operator structure needed for the test
        # and the latest commit is the change being tested. This means we need
        # to exclude the latest commit when pushing to the operator repo.
        local_repo.create_head(
            # create local contributor branch
            "contributor",
            commit="HEAD",
        )
        local_repo.remotes.contributor.push(
            # force push local contributor branch to test branch in contributor repo
            f"+contributor:{remote_branch}"
        )
        local_repo.create_head(
            # create local operators branch discarding latest commit
            "operators",
            commit="HEAD~1",
        )
        local_repo.remotes.operators.push(
            # force push local operators branch to test branch in operators repo
            f"+operators:{remote_branch}"
        )
        # TODO: create github webhook
        # TODO: create github PR

    def watch(self) -> None:
        # TODO: wait until pipelinerun finishes
        pass

    def validate(self) -> None:
        # TODO: check pipelinerun status
        # TODO: check generated bundle image
        # TODO: check bundle is in index
        pass

    def cleanup(self) -> None:
        # TODO: remove bundle image
        # TODO: remove index image
        # TODO: remove github webhook
        # TODO: delete test git branches
        # remove temp dir
        if self.tempdir:
            rmtree(self.tempdir, ignore_errors=True)
