#!/usr/bin/env bash

set -e
set -u

BASEDIR=$HOME/conp-dataset
mkdir -p ${BASEDIR}/log
DATE=$(date)
LOGFILE=$(mktemp ${BASEDIR}/log/crawler-XXXXX.log)
TOUCHFILE=${BASEDIR}/.crawling
# Add user tokens here (separated by space), or edit file $HOME/.token
TOKEN_LIST="w4M00bgKOLzWDCHdFGeXc2wzaE9ftmedZAcneqTQEO9qQK4G3A7ez7CfOS7Y"

echo  "**** STARTING ZENODO CRAWL at ${DATE}, LOGGING IN ${LOGFILE} ****" &>>$HOME/crawl_zenodo.log
test -f ${TOUCHFILE} && (echo "Another crawling process is still running (${TOUCHFILE} exists), exiting!" &>>${LOGFILE}; exit 1 )

# We are in the protected section
touch ${TOUCHFILE}

(cd ${BASEDIR} && git pull --no-edit main master)

python3 ./scripts/crawl_zenodo.py --verbose -z ${TOKEN_LIST} &>>${LOGFILE}
