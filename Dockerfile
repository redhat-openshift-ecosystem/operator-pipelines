FROM quay.io/fedora/fedora:43

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

USER root

# setup certificates
COPY certs/* /etc/pki/ca-trust/source/anchors/
RUN /usr/bin/update-ca-trust
# This is just a temporary workaround until we figure out how to
# override CA bundle in OCP
RUN cp /etc/pki/tls/certs/ca-bundle.crt /etc/pki/tls/certs/custom-ca-bundle.crt

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

# Install oc, opm and operator-sdk CLI
RUN curl -LO https://github.com/operator-framework/operator-registry/releases/download/v1.46.0/linux-${ARCH}-opm && \
  chmod +x linux-${ARCH}-opm && \
  mv linux-${ARCH}-opm /usr/local/bin/opm && \
  curl -LO https://mirror.openshift.com/pub/openshift-v4/${ARCH}/clients/ocp/stable-4.20/openshift-client-linux.tar.gz && \
  tar xzvf openshift-client-linux.tar.gz -C /usr/local/bin oc && \
  curl -LO https://github.com/operator-framework/operator-sdk/releases/download/v1.36.1/operator-sdk_linux_${ARCH} && \
  chmod +x operator-sdk_linux_${ARCH} && \
  mv operator-sdk_linux_${ARCH} /usr/local/bin/operator-sdk

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

ENTRYPOINT [ "/usr/bin/sh" ]
