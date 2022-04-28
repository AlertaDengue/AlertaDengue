#!/bin/bash

echo "Create environment variables..."
envsubst < /opt/services/AlertaDengue/env.tpl > /opt/services/AlertaDengue/.env
echo "Start crontab..."
sudo service cron start
echo "Start django..."
bash /opt/services/AlertaDengue/runwsgi.sh
