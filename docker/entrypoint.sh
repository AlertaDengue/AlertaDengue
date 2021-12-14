#!/bin/bash
echo "Executing the entrypoint!"
echo "Install python packages..."
envsubst < /srv/deploy/.env.tmpl > /srv/deploy/.env \
&& pip install .
echo "Start crontab..."
sudo service cron start & tail -f /var/log/cron.log
