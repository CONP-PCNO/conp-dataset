FROM ubuntu:focal
LABEL maintainer="mathieu.dugre@concordia.ca"
LABEL Name=conp-dataset Version=0.0.1

RUN : \
    && apt-get -yq update \
    && apt-get install -yq --no-install-recommends \
        python3-dev \
        python3-pip \
        curl \
        openssh-client \
        netbase \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && :

# Retrieve the binaries for the latest version of git-annex.
RUN : \
    && curl \
        https://downloads.kitenet.net/git-annex/linux/current/git-annex-standalone-amd64.tar.gz \
        | tar -zxvf - \
    && sh /git-annex.linux/runshell \
    && :
ENV PATH="/git-annex.linux:${PATH}"

# Retrieve lastest version of conp-dataset.
RUN : \
    && git clone \
        --progress \
        --depth=1 \
        https://github.com/CONP-PCNO/conp-dataset  \
        /conp-dataset \
    && :
WORKDIR /conp-dataset

# Install dependencies.
RUN : \
    && find . -name requirements.txt | xargs -I{} pip3 install --quiet -r {} \
    && :

# Prepare the image for running tests, if needed.
RUN : \
    && datalad install -r scripts/dats_validator \
    && python3 tests/create_tests.py \
    && :
ENV PYTHONPATH=/conp-dataset

CMD [ "bash" ]
