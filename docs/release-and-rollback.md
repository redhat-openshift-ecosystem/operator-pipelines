### Release Schedule

Every Monday and Wednesday, except for hotfixes.

### Hotfixes
Hotfixes are defined as changes that need to be quickly deployed to prod, outside of the regular release schedule, to address major issues that occur in prod. Hotfixes should still follow the release criteria and process, and should be announced on the team chat so that the rest of the team is aware.


### Release Criteria
* Change is submitted as a pull request on Github.
* All checks (validations and tests) pass on the pull request.
* Pull request is reviewed and approved by at least one other ISV Guild member.
* Change is merged into main branch.
* A new release must be deployed to dev and qa before being deployed to stage
* A new release must be deployed to stage in the previous scheduled release date before being deployed to prod
    * Stage and prod deployments are manually triggered by approving the related Github Actions.

### Release Process
Before deployments occur, a new container image will be built and with “latest” and the associated git commit sha, then pushed to quay.io.

Dev and qa deployment will happen automatically by Github Actions every time a change is merged into the main branch. The commit sha will be passed for identify the container image used by the pipelines as part of deployments.

During a scheduled release or hotfix, stage and prod deployment will only happen by manually triggering the “deploy-stage” and “deploy-prod” Github Actions respectively. In a scheduled release, changes that were previously deployed to dev and qa will be promoted to stage, and changes that were previously deployed to stage will be promoted to prod. The last container image used in dev and qa (identified by the git commit sha tag) will also be promoted to be used in the stage pipeline, while the container image last used in stage will be used in the prod pipeline.



### Rollback Process
#### Short term rollbacks
For short term rollbacks: Re-run deployment from a previous stable release. Since the container image is identified by the git commit sha, re-running a previous deployment will also roll back the container image that’s used to a previous one.

#### Longer term rollbacks
Revert commit(s) that need to be rolled back, then follow the regular release process to deploy.
