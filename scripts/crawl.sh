#!/usr/bin/env bash

set -e
set -u

BASEDIR=/tmp/conp-dataset
mkdir -p ${BASEDIR}/log
DATE=$(date)
LOGFILE=$(mktemp ${BASEDIR}/log/crawler-XXXXX.log)
TOUCHFILE=${BASEDIR}/.crawling
# Edit file $HOME/.conp_crawler_config.json to add tokens

echo  "**** STARTING CRAWL at ${DATE}, LOGGING IN ${LOGFILE} ****" &>>$HOME/crawl.log
test -f ${TOUCHFILE} && (echo "Another crawling process is still running (${TOUCHFILE} exists), exiting!" &>>${LOGFILE}; exit 1 )

# We are in the protected section
touch ${TOUCHFILE}

cd ${BASEDIR} && git pull --no-edit main master

python3 ./scripts/crawl.py --verbose &>>${LOGFILE}
