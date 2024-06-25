-include .env
-include .set_env

# Default tag is gnerated from the current timestamp
TAG ?= $(shell date +%s)
PIPELINE_IMAGE_REPO ?= quay.io/redhat-isv/operator-pipelines-test-image
PIPELINE_IMAGE ?= $(PIPELINE_IMAGE_REPO):$(TAG)
# For local tests use a version-release based on the latest sucesfull
# pipeline run in Github action and bump up the release number
# https://github.com/redhat-openshift-ecosystem/operator-pipelines/actions/workflows/integration-tests.yml
OPERATOR_VERSION_RELEASE ?= 1-1
OPERATOR_VERSION ?= 0.1.$(OPERATOR_VERSION_RELEASE)

.PHONY: build-and-deploy-playground
build-and-deploy-playground:
	@echo "Building and deploying playground..."
	$(MAKE) build
	$(MAKE) deploy-playground TAG=$(TAG)

.PHONY: deploy-playground
deploy-playground:
	@echo "Deploying playground..."
	ansible-playbook \
		ansible/playbooks/deploy.yml \
		--inventory ansible/inventory/operator-pipeline-stage \
		-e oc_namespace=$(USER)-playground \
		-e operator_bundle_version=$(OPERATOR_VERSION) \
		-e operator_pipeline_image_pull_spec=$(PIPELINE_IMAGE) \
		-e suffix=123 \
		-e ocp_token=`oc whoami -t` \
		-e branch=$(USER) \
		-e env=stage \
		--skip-tags ci,import-index-images \
		-vv \
		--vault-password-file ansible/vault-password

.PHONY: build-and-test-isv
build-and-test-isv:
	@echo "Building and testing ISV operator pipelines..."
	$(MAKE) build
	$(MAKE) integration-test-isv TAG=$(TAG)

.PHONY: build-and-test-community
build-and-test-community:
	@echo "Building and testing community operator pipelines..."
	$(MAKE) build
	$(MAKE) integration-test-community TAG=$(TAG)


.PHONY: build
build:
	@echo "Building..."
	podman build -t pipelines . -f operator-pipeline-images/Dockerfile
	@echo "Tagging..."
	podman tag pipelines $(PIPELINE_IMAGE_REPO):$(TAG)
	podman push $(PIPELINE_IMAGE_REPO):$(TAG)

.PHONY: integration-test-isv
integration-test-isv:
	ansible-playbook \
		ansible/playbooks/operator-pipeline-integration-tests.yml \
		-i ansible/inventory/operator-pipeline-integration-tests \
		-e oc_namespace=$(USER)-isv-test-$(OPERATOR_VERSION_RELEASE) \
		-e operator_bundle_version=$(OPERATOR_VERSION) \
		-e operator_pipeline_image_pull_spec=$(PIPELINE_IMAGE) \
		-e suffix=123 \
		--skip-tags=signing-pipeline \
		-vv \
		--vault-password-file ansible/vault-password

.PHONY: integration-test-community
integration-test-community:
	@echo "Running integration tests..."
	ansible-playbook \
		ansible/playbooks/community-operators-integration-tests.yaml \
		-i ansible/inventory/operator-pipeline-integration-tests \
		-e oc_namespace=$(USER)-comm-test-$(OPERATOR_VERSION_RELEASE) \
		-e operator_bundle_version=$(OPERATOR_VERSION) \
		-e operator_pipeline_image_pull_spec=$(PIPELINE_IMAGE) \
		-e suffix=8c6beec \
		--skip-tags=signing-pipeline,import-index-images \
		-vv \
		--vault-password-file ansible/vault-password
