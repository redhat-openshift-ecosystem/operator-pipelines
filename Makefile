-include .env
-include .set_env


.PHONY: build
build:
	@echo "Building..."
	podman build -t pipelines . -f operator-pipeline-images/Dockerfile

	podman tag pipelines quay.io/redhat-isv/operator-pipelines-test-image:$$USER

	podman push quay.io/redhat-isv/operator-pipelines-test-image:$$USER

.PHONY: integration-test
integration-test:
	ansible-playbook \
		playbooks/operator-pipeline-integration-tests.yml \
		-i inventory/operator-pipeline-integration-tests \
		-e oc_namespace=integration-tests-1-0 \
		-e operator_bundle_version=0.1.1-1 \
		-e operator_pipeline_image_pull_spec=quay.io/redhat-isv/operator-pipelines-test-image:$$USER \
		-e suffix=123 \
		-v \
		--vault-password-file vault-password
