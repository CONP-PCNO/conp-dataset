FROM debian:stable

WORKDIR /src

RUN apt-get -qq update && apt-get -qq -y install curl bzip2 \
    && curl -sSL https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -bfp /src/miniconda \
    && rm -rf /tmp/miniconda.sh \
    && apt-get -qq -y remove curl bzip2 \
    && apt-get -qq -y autoremove \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* /var/log/dpkg.log \
    && rm -r /src/miniconda/pkgs

ENV PATH "/src/miniconda/bin/:$PATH"

RUN conda install -y -c conda-forge git-annex \
    && rm -r /src/miniconda/pkgs