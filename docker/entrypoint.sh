#!/bin/bash

echo "Create environment variables..."
envsubst < /opt/services/AlertaDengue/env.tpl > /opt/services/AlertaDengue/.env
echo "Start crontab..."
sudo service cron start

if [ $# -ne 0 ]
  then
    exec "$@"
fi
