FROM ubuntu:22.04

ARG XNAT_UNAME=${XNAT_UNAME}
ARG XNAT_GROUP=${XNAT_GROUP}
ARG XNAT_UID=${XNAT_UID}
ARG XNAT_GID=${XNAT_GID}

ENV TZ=America/Chicago \
    PYTHONUNBUFFERED=1 \
    VENV="/opt/venv" \
    PYTHON_VERSION="3.10" \
    UV_NO_CACHE="true" \
    UV_PYTHON_INSTALL_DIR="/usr/local/bin" \
    PATH="/opt/venv/bin:${PATH}"

RUN apt-get update -y && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        sudo \
        tzdata \
        ca-certificates && \
    ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime && \
    echo ${TZ} > /etc/timezone && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --chmod=775 --from=ghcr.io/astral-sh/uv:alpine /usr/local/bin/uv /usr/bin/uv

RUN groupadd -g ${XNAT_GID} ${XNAT_GROUP} && \
    useradd -m -s /bin/bash -u ${XNAT_UID} -g ${XNAT_GID} -G sudo -l ${XNAT_UNAME} && \
    printf "\n\n%s ALL=(ALL) NOPASSWD:ALL\n\n" "${XNAT_UNAME}" >> /etc/sudoers && \
    mkdir -p $(dirname ${VENV}) /app /data/models/.auth /data/models/.logs && \
    chown -R ${XNAT_UNAME}:${XNAT_GROUP} $(dirname ${VENV}) /app /data

RUN uv python install ${PYTHON_VERSION}

USER ${XNAT_UID}

WORKDIR /app

ENV PATH="${PATH}:/home/${XNAT_UNAME}/.local/bin" 

COPY --chown=${XNAT_UNAME}:${XNAT_GROUP} requirements.txt ./
RUN uv venv --python ${PYTHON_VERSION} ${VENV} && \
    . ${VENV}/bin/activate && \
    uv pip install -U pip && \
    uv pip install -r requirements.txt

COPY --chmod=775 --chown=${XNAT_UNAME}:${XNAT_GROUP} src /app/model-dashboard
COPY --chmod=775 --chown=${XNAT_UNAME}:${XNAT_GROUP} scripts /app/scripts

RUN uv pip install -e /app/model-dashboard

COPY --chmod=775 --chown=${XNAT_UNAME}:${XNAT_GROUP} config /app/model-dashboard/model_dashboard/.streamlit

# Expose both Streamlit and API ports
EXPOSE 8501 8000

# Default to running both dashboard and API
ENTRYPOINT ["model-dashboard-all"]