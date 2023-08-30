FROM registry.fedoraproject.org/fedora:38

LABEL description="Cli tools for operator certification pipeline"
LABEL summary="This image contains tools required for operator bundle certification pipeline."

ARG USER_UID=1000
ARG PODMAN_USER_UID=1001
ARG ARCH=amd64


USER root

# setup certificates
COPY operator-pipeline-images/certs/* /etc/pki/ca-trust/source/anchors/
RUN /usr/bin/update-ca-trust

# This is just a temporary workaround until we figure out how to
# override CA bundle in OCP
RUN cp /etc/pki/tls/certs/ca-bundle.crt /etc/pki/tls/certs/custom-ca-bundle.crt

ENV REQUESTS_CA_BUNDLE="/etc/pki/tls/certs/custom-ca-bundle.crt"

RUN dnf update -y && \
    dnf install -y \
    findutils \
    git \
    gcc \
    gh \
    gnupg2 \
    jq \
    cargo \
    libffi-devel \
    redhat-rpm-config \
    krb5-devel \
    krb5-workstation \
    yamllint \
    openssl-devel \
    pinentry \
    pip \
    podman \
    python3-devel \
    skopeo && \
    dnf clean all

COPY operator-pipeline-images/config/krb5.conf /etc/krb5.conf

# Install oc, opm and operator-sdk CLI
RUN curl -LO https://github.com/operator-framework/operator-registry/releases/download/v1.26.2/linux-${ARCH}-opm && \
    chmod +x linux-${ARCH}-opm && \
    mv linux-${ARCH}-opm /usr/local/bin/opm && \
    curl -LO https://mirror.openshift.com/pub/openshift-v4/${ARCH}/clients/ocp/latest-4.10/openshift-client-linux.tar.gz && \
    tar xzvf openshift-client-linux.tar.gz -C /usr/local/bin oc && \
    curl -LO https://github.com/operator-framework/operator-sdk/releases/download/v1.31.0/operator-sdk_linux_${ARCH} && \
    chmod +x operator-sdk_linux_${ARCH} && \
    mv operator-sdk_linux_${ARCH} /usr/local/bin/operator-sdk

RUN useradd -ms /bin/bash -u "${USER_UID}" user

RUN useradd -u "${PODMAN_USER_UID}" podman; \
    echo podman:10000:5000 > /etc/subuid; \
    echo podman:10000:5000 > /etc/subgid;


WORKDIR /home/user

COPY ./operator-pipeline-images ./

# install PDM
RUN pip3 install --upgrade pip setuptools wheel && pip3 install pdm
# install dependencies in virtual environment
COPY ./pdm.lock ./pyproject.toml ./README.md ./
RUN pdm venv create 3.11 && pdm install --no-lock --no-editable \
        --group operatorcert \
        --group operatorcert-dev

ENV VIRTUAL_ENV=/home/user/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# set dir ownership
RUN chgrp -R 0 /home/user /etc/passwd
RUN chmod -R g=u /home/user /etc/passwd

USER "${USER_UID}"