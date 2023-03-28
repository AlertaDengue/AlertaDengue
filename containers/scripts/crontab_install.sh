#!/usr/bin/env bash

service cron restart
chmod 0644  /etc/cron.d/cronjob
crontab -u deploy  /etc/cron.d/cronjob
touch /var/log/cron.log
touch /var/run/crond.pid
chown deploy:deploy /var/log/cron.log
chown deploy:deploy /var/run/crond.pid
