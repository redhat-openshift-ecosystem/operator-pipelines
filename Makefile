-include .env
-include .set_env

# Default tag is generated from the current timestamp
TAG ?= $(shell date +%s)
PIPELINE_IMAGE_REPO ?= quay.io/redhat-isv/operator-pipelines-test-image
PIPELINE_IMAGE ?= $(PIPELINE_IMAGE_REPO):$(TAG)
# For local tests use a version-release based on the latest successful
# pipeline run in Github action and bump up the release number
# https://github.com/redhat-openshift-ecosystem/operator-pipelines/actions/workflows/integration-tests.yml
OPERATOR_VERSION_RELEASE ?= 1-1
OPERATOR_VERSION ?= 0.1.$(OPERATOR_VERSION_RELEASE)


.PHONY: configure-stage-cluster
configure-stage-cluster:
	@echo "Configuring stage cluster..."
	ansible-playbook \
		ansible/playbooks/config-ocp-cluster.yml \
		-e clusters=stage-cluster \
		-i ansible/inventory/clusters \
		--vault-password-file ansible/vault-password

.PHONY: configure-prod-cluster
configure-prod-cluster:
	@echo "Configuring prod cluster..."
	ansible-playbook \
		ansible/playbooks/config-ocp-cluster.yml \
		-e clusters=prod-cluster \
		-i ansible/inventory/clusters \
		--vault-password-file ansible/vault-password-prod

.PHONY: build-and-deploy-playground
build-and-deploy-playground:
	@echo "Building and deploying playground..."
	$(MAKE) build
	$(MAKE) deploy-playground TAG=$(TAG)

.PHONY: deploy-playground
deploy-playground:
	@echo "Deploying playground..."
	ansible-playbook \
		ansible/playbooks/deploy-playground.yml \
		-e oc_namespace=$(USER)-playground \
		-e integration_tests_operator_bundle_version=$(OPERATOR_VERSION) \
		-e operator_pipeline_image_pull_spec=$(PIPELINE_IMAGE) \
		-e suffix=123 \
		-e ocp_token=`oc whoami -t` \
		-e branch=$(USER) \
		-e operator_pipeline_github_user=$(GITHUB_USER) \
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

.PHONY: build-and-test-isv-fbc-bundle
build-and-test-isv-fbc-bundle:
	@echo "Building and testing isv FBC operator pipelines..."
	$(MAKE) build
	$(MAKE) integration-test-isv-fbc-bundle TAG=$(TAG)

.PHONY: build-and-test-isv-fbc-catalog
build-and-test-isv-fbc-catalog:
	@echo "Building and testing isv FBC catalog pipelines..."
	$(MAKE) build
	$(MAKE) integration-test-isv-fbc-catalog TAG=$(TAG)


.PHONY: build
build:
	@echo "Building..."
	podman build -t pipelines . -f Dockerfile
	@echo "Tagging..."
	podman tag pipelines $(PIPELINE_IMAGE_REPO):$(TAG)
	podman push $(PIPELINE_IMAGE_REPO):$(TAG)

.PHONY: integration-test-isv
integration-test-isv:
	ansible-playbook \
		ansible/playbooks/operator-pipeline-integration-tests.yml \
		-e test_type=isv \
		-e oc_namespace=$(USER)-isv-test-$(OPERATOR_VERSION_RELEASE) \
		-e integration_tests_operator_bundle_version=$(OPERATOR_VERSION) \
		-e operator_pipeline_image_pull_spec=$(PIPELINE_IMAGE) \
		-e suffix=123 \
		--skip-tags=signing-pipeline \
		-vv \
		--vault-password-file ansible/vault-password

.PHONY: integration-test-community
integration-test-community:
	@echo "Running integration tests..."
	ansible-playbook \
		ansible/playbooks/operator-pipeline-integration-tests.yml \
		-e test_type=community \
		-e oc_namespace=$(USER)-comm-test-$(OPERATOR_VERSION_RELEASE) \
		-e integration_tests_operator_bundle_version=$(OPERATOR_VERSION) \
		-e operator_pipeline_image_pull_spec=$(PIPELINE_IMAGE) \
		-e suffix=8c6beec \
		--skip-tags=signing-pipeline,import-index-images \
		-vv \
		--vault-password-file ansible/vault-password

.PHONY: integration-test-isv-fbc-bundle
integration-test-isv-fbc-bundle:
	@echo "Running integration tests..."
	ansible-playbook \
		ansible/playbooks/operator-pipeline-integration-tests.yml \
		-e test_type=isv-fbc-bundle \
		-e oc_namespace=$(USER)-isv-fbc-bundle-test-$(OPERATOR_VERSION_RELEASE) \
		-e integration_tests_operator_bundle_version=$(OPERATOR_VERSION) \
		-e operator_pipeline_image_pull_spec=$(PIPELINE_IMAGE) \
		-e suffix=8c6beec \
		--skip-tags=signing-pipeline \
		-vv \
		--vault-password-file ansible/vault-password

.PHONY: integration-test-isv-fbc-catalog
integration-test-isv-fbc-catalog:
	@echo "Running integration tests..."
	ansible-playbook \
		ansible/playbooks/operator-pipeline-integration-tests.yml \
		-e test_type=isv-fbc-catalog \
		-e oc_namespace=$(USER)-fbc-catalog-test-$(OPERATOR_VERSION_RELEASE) \
		-e integration_tests_operator_bundle_version=$(OPERATOR_VERSION) \
		-e operator_pipeline_image_pull_spec=$(PIPELINE_IMAGE) \
		-e suffix=8c6beec \
		--skip-tags=signing-pipeline \
		-vvvv \
		--vault-password-file ansible/vault-password
