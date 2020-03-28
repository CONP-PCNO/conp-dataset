FROM neurodebian:bionic

RUN apt-get -qq update \
    && apt-get -qq -y install git-annex-standalone python3-pip python3-venv \
    && apt-get -qq -y autoremove \
    && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* /var/log/dpkg.log

RUN ln -s /usr/bin/python3 /usr/bin/python \
    && ln -s /usr/bin/pip3 /usr/bin/pip
