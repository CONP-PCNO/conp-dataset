FROM circleci/python:3.9

WORKDIR /home/circleci

RUN curl https://downloads.kitenet.net/git-annex/linux/current/git-annex-standalone-amd64.tar.gz | tar -zxvf - \
    && sh ~/git-annex.linux/runshell

RUN git config --global user.name "circleci" \
    && git config --global user.email "circleci@mathdugre.me"
