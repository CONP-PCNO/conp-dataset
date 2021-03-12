#!/usr/bin/env bash

set -e
set -u

# Check for if BASEDIR is set, else set to /data/crawler/conp-dataset
if ! [[ -v BASEDIR ]]; then
  BASEDIR=/data/crawler/conp-dataset
fi

mkdir -p ${BASEDIR}/log
DATE=$(date)
LOGFILE=$(mktemp ${BASEDIR}/log/crawler-XXXXX.log)
TOUCHFILE=${BASEDIR}/.crawling
# Edit file $HOME/.conp_crawler_config.json to add tokens

echo  "**** STARTING CRAWL at ${DATE}, LOGGING IN ${LOGFILE} ****" &>>$HOME/crawl.log
test -f ${TOUCHFILE} && (echo "Another crawling process is still running (${TOUCHFILE} exists), exiting!" &>>${LOGFILE}; exit 1 )

# We are in the protected section
touch ${TOUCHFILE}

cd ${BASEDIR}
if git pull --no-edit main master &>>${LOGFILE}
then
  python3 ./scripts/crawl.py --verbose &>>${LOGFILE}; rm ${TOUCHFILE}; exit 0
else
  echo "ERROR: git pull failed, did not run crawl.py script" &>>${LOGFILE}; rm ${TOUCHFILE}; exit 1
fi
