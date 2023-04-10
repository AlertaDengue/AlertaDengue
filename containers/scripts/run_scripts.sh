#!/usr/bin/env bash

echo -e "[II] configuring crontab for the deploy user..."
sudo bash /opt/services/scripts/crontab_install.sh

echo -e "[II] exporting environment variables..."
bash /opt/services/scripts/export-env.sh

echo -e "[II] Starting django..."
bash /opt/services/AlertaDengue/runwsgi.sh
