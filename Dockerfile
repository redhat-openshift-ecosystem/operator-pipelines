FROM registry.fedoraproject.org/fedora:34

LABEL description="Cli tools for operator certification pipeline"
LABEL summary="This image contains tools required for operator bundle certification pipeline."


ARG USER_UID=1000

USER root

RUN dnf update -y && \
    dnf install -y \
    git \
    jq \
    openssl-devel \
    pip \
    python3-devel && \
    dnf clean all

RUN curl -LO https://github.com/operator-framework/operator-sdk/releases/download/v1.8.1/operator-sdk_linux_amd64 && \
    chmod +x operator-sdk_linux_amd64 && \
    mv operator-sdk_linux_amd64 /usr/local/bin/operator-sdk

RUN useradd -ms /bin/bash -u "${USER_UID}" user

WORKDIR /home/user


COPY requirements.txt ./
COPY scripts/ scripts/

ENV PATH="/home/user/scripts:${PATH}"

RUN pip3 install -r requirements.txt

# set dir ownership
RUN chgrp -R 0 /home/user /etc/passwd
RUN chmod -R g=u /home/user /etc/passwd

USER "${USER_UID}"
