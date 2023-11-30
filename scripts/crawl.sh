#!/usr/bin/env bash

set -e
set -u

# Check for if BASEDIR is set, else set to /data/crawler/conp-dataset
if ! [[ -v BASEDIR ]]; then
  export BASEDIR=/data/crawler/conp-dataset
fi

mkdir -p ${BASEDIR}/log
DATE=$(date)
LOGFILE=$(mktemp ${BASEDIR}/log/crawler-XXXXX.log)
TOUCHFILE=${BASEDIR}/.crawling
# Edit file $HOME/.conp_crawler_config.json to add tokens

echo  "**** STARTING CRAWL at ${DATE}, LOGGING IN ${LOGFILE} ****"  2>&1 | tee $HOME/crawl.log
test -f ${TOUCHFILE} && (echo "Another crawling process is still running (${TOUCHFILE} exists), exiting!"  2>&1 | tee ${LOGFILE}; exit 1 )

# We are in the protected section
touch ${TOUCHFILE}

cd ${BASEDIR}
if git pull --no-edit main master  2>&1 | tee ${LOGFILE}
then
  python3 ./scripts/crawl.py --verbose  2>&1 | tee ${LOGFILE}; rm ${TOUCHFILE}; exit 0
else
  echo "ERROR: git pull failed, did not run crawl.py script"  2>&1 | tee ${LOGFILE}; rm ${TOUCHFILE}; exit 1
fi
