#!/bin/bash

echo "Create environment variables..."
envsubst < /srv/deploy/.env.tmpl > /srv/deploy/.env
echo "Start crontab..."
sudo service cron start
echo "Start django..."
bash /srv/deploy/AlertaDengue/runwsgi.sh
