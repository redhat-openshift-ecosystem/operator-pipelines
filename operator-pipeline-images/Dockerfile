FROM registry.fedoraproject.org/fedora:34

LABEL description="Cli tools for operator certification pipeline"
LABEL summary="This image contains tools required for operator bundle certification pipeline."

ARG USER_UID=1000
ARG PODMAN_USER_UID=1001


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
    gnupg2 \
    jq \
    krb5-devel \
    krb5-workstation \
    yamllint \
    openssl-devel \
    origin-clients \
    pinentry \
    pip \
    podman \
    python3-devel && \
    dnf clean all

COPY operator-pipeline-images/config/krb5.conf /etc/krb5.conf

# Install opm CLI
RUN curl -LO https://github.com/operator-framework/operator-registry/releases/download/v1.19.5/linux-amd64-opm && \
    chmod +x linux-amd64-opm && \
    mv linux-amd64-opm /usr/local/bin/opm

RUN useradd -ms /bin/bash -u "${USER_UID}" user

RUN useradd -u "${PODMAN_USER_UID}" podman; \
    echo podman:10000:5000 > /etc/subuid; \
    echo podman:10000:5000 > /etc/subgid;


WORKDIR /home/user

COPY ./operator-pipeline-images ./

RUN pip3 install .

# set dir ownership
RUN chgrp -R 0 /home/user /etc/passwd
RUN chmod -R g=u /home/user /etc/passwd

USER "${USER_UID}"
