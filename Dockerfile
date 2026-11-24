FROM ubuntu:24.04
LABEL maintainer="anthony.hatzopoulos@mcin.ca"
LABEL name=conp-dataset version=0.0.1

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

RUN : \
    && apt-get -yq update \
    && apt-get install -yq --no-install-recommends \
        python3-dev=3.12.3-0ubuntu2.1 \
        python3-venv=3.12.3-0ubuntu2.1 \
        curl=8.5.0-2ubuntu10.16 \
        git=1:2.43.0-1ubuntu7.4 \
        openssh-client=1:9.6p1-3ubuntu13.20 \
        netbase=6.4 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && :
ENV UV_PYTHON_DOWNLOADS=never

# Retrieve the binaries for the latest version of git-annex.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN : \
    && curl \
        https://downloads.kitenet.net/git-annex/linux/current/git-annex-standalone-amd64.tar.gz \
        | tar -zxvf - \
    && sh /git-annex.linux/runshell \
    && :
ENV PATH="/git-annex.linux:${PATH}"

# Setup Git for GitHub Actions
RUN : \
    && git config --global user.email "action@github.com" \
    && git config --global user.name "GitHub Action" \
    && :

# Retrieve lastest version of conp-dataset.
RUN : \
    && git clone \
        --progress \
        --depth=1 \
        https://github.com/CONP-PCNO/conp-dataset  \
        /conp-dataset \
    && :
WORKDIR /conp-dataset

# Install Python dependencies from the locked project configuration.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN uv sync --locked --all-groups

# Prepare the image for running tests, if needed.
RUN : \
    && datalad install -r scripts \
    && python tests/create_tests.py \
    && :
ENV PYTHONPATH=/conp-dataset

CMD [ "bash" ]
