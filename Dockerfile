FROM quay.io/fedora/fedora:44

LABEL description="Cli tools for operator certification pipeline"
LABEL summary="This image contains tools required for operator bundle certification pipeline."

LABEL org.opencontainers.image.authors="The Collective <exd-guild-isv@redhat.com>" \
  org.opencontainers.image.url="quay.io/redhat-isv/operator-pipelines-images" \
  org.opencontainers.image.source="https://github.com/redhat-openshift-ecosystem/operator-pipelines" \
  org.opencontainers.image.vendor="Red Hat." \
  org.opencontainers.image.title="Operator certification tools" \
  org.opencontainers.image.description="Cli tools for operator certification pipeline." \
  org.opencontainers.image.base.name="quay.io/fedora/fedora:42"

ARG USER_UID=1000
ARG PODMAN_USER_UID=1001
ARG ARCH=amd64

ARG OPM_VERSION=v1.71.0
ARG OCP_VERSION=4.20.35
ARG OPERATOR_SDK_VERSION=v1.36.1

# https://github.com/operator-framework/operator-registry/releases/download/v1.71.0/linux-amd64-opm
ARG OPM_SHA256=a9c9193dd727a11966f98919a4805328554c439d3f7e72a095b4eb4a437dcd9f
# https://mirror.openshift.com/pub/openshift-v4/amd64/clients/ocp/4.20.35/openshift-client-linux.tar.gz
ARG OC_SHA256=35ce9f9a21d1524f811f035b730aa0b51879df73343fb3d59d618b88b0f1b968
# https://github.com/operator-framework/operator-sdk/releases/download/v1.36.1/operator-sdk_linux_amd64
ARG OPERATOR_SDK_SHA256=25872268c422fb63a350d85741a1f26052c953c7e9654167b0e8dbd6dbfb6c1d

USER root

# setup certificates
COPY certs/* /etc/pki/ca-trust/source/anchors/
RUN /usr/bin/update-ca-trust
# This is just a temporary workaround until we figure out how to
# override CA bundle in OCP
RUN cp /etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt /etc/pki/tls/certs/custom-ca-bundle.crt

ENV REQUESTS_CA_BUNDLE="/etc/pki/tls/certs/custom-ca-bundle.crt"

# Install all system dependencies including Python and development tools
RUN dnf update -y && \
  dnf install -y \
  buildah \
  cargo \
  findutils \
  gcc \
  gh \
  git \
  gnupg2 \
  jq \
  krb5-devel \
  krb5-workstation \
  libffi-devel \
  openssl-devel \
  pinentry \
  podman \
  python3 \
  python3-devel \
  python3-pip \
  redhat-rpm-config \
  skopeo \
  yamllint && \
  dnf clean all

COPY config/krb5.conf /etc/krb5.conf
COPY hacks/retry-command.sh /usr/local/bin/retry

# Set the SHELL option -o pipefail before RUN with a pipe in it. (hadolint)
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install oc, opm and operator-sdk CLI
RUN curl -LO https://github.com/operator-framework/operator-registry/releases/download/${OPM_VERSION}/linux-${ARCH}-opm && \
  echo "${OPM_SHA256}  linux-${ARCH}-opm" | sha256sum -c - && \
  chmod +x linux-${ARCH}-opm && \
  mv linux-${ARCH}-opm /usr/local/bin/opm && \
  curl -LO https://mirror.openshift.com/pub/openshift-v4/${ARCH}/clients/ocp/${OCP_VERSION}/openshift-client-linux.tar.gz && \
  echo "${OC_SHA256}  openshift-client-linux.tar.gz" | sha256sum -c - && \
  tar xzvf openshift-client-linux.tar.gz -C /usr/local/bin oc && \
  curl -LO https://github.com/operator-framework/operator-sdk/releases/download/${OPERATOR_SDK_VERSION}/operator-sdk_linux_${ARCH} && \
  echo "${OPERATOR_SDK_SHA256}  operator-sdk_linux_${ARCH}" | sha256sum -c - && \
  chmod +x operator-sdk_linux_${ARCH} && \
  mv operator-sdk_linux_${ARCH} /usr/local/bin/operator-sdk

# Install leaktkt
COPY --from=quay.io/leaktk/leaktk:0.3.5@sha256:47f6120b372bc29629f00812ab363496321f1ab412b4d4a908516d50a2443617  /usr/local/bin/leaktk /usr/local/bin/

# Create users
RUN useradd -lms /bin/bash -u "${USER_UID}" user && \
  useradd -lu "${PODMAN_USER_UID}" podman; \
  echo podman:10000:5000 >> /etc/subuid; \
  echo podman:10000:5000 >> /etc/subgid;

WORKDIR /home/user

# Set directory ownership
RUN chgrp -R 0 /home/user /etc/passwd && \
  chmod -R g=u /home/user /etc/passwd

# Install Poetry
RUN pip3 install --no-cache-dir --upgrade poetry==2.3.1

# Copy only dependency files first (better caching)
COPY pyproject.toml poetry.lock /home/user/

# Configure Poetry for container optimization
ENV POETRY_VIRTUALENVS_IN_PROJECT=true \
  POETRY_CACHE_DIR=/tmp/poetry_cache

# Install dependencies in separate layer (cached until deps change)
RUN poetry install --without dev --no-root && \
  rm -rf /tmp/poetry_cache

# Copy code AFTER deps (doesn't bust dependency cache)
COPY operatorcert ./operatorcert
COPY README.md ./

# Install the package itself (quick since deps already installed)
RUN poetry install --only-root

# Set up PATH to use the virtual environment
ENV PATH=/home/user/.venv/bin:$PATH

USER "${USER_UID}"
