#!/usr/bin/env bash

echo "[INFO] Load variables..."
envsubst < .env.tpl > AlertaDengue/.env

echo "[INFO] Configuring crontab..."
sudo chmod 0644  /etc/cron.d/cronjob
sudo crontab -u deploy  /etc/cron.d/cronjob
sudo touch /var/log/cron.log
sudo touch /var/run/crond.pid
sudo chown deploy:deploy /var/log/cron.log
sudo chown deploy:deploy /var/run/crond.pid
sudo service cron restart
