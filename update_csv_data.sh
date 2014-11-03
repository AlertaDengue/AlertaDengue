#!/bin/bash
HOST=$1
FILEPATH=$2
if [ -z $HOST ] || [ -z $FILEPATH ]
then
    echo "usage: $0 <hostname> <data_file_path>"
    exit 1
fi

set -e

echo "Uploading new data file..."
scp -o 'Port 2222' $FILEPATH root@$HOST:/srv/deploy/project/AlertaDengue/AlertaDengue/data/alertaAPS.csv
echo "... Done"

echo "Fixing data file permissions..."
# I could not make ssh to the deploy user work, so for now I'll just upload the
# file as root and fix permissions.
ssh -p 2222 root@$HOST chown -R deploy:deploy /srv/deploy/project/AlertaDengue/AlertaDengue/data/
echo "... Done"

echo "Restarting service..."
ssh -p 2222 root@$HOST supervisorctl restart alerta_dengue
echo "... Done"
