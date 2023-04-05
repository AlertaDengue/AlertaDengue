#!/usr/bin/env bash

echo -n "[II] configuring crontab for the deploy user... "
sudo bash /opt/services/scripts/crontab_install.sh

echo -n "[II] exporting environment variables... "
bash /opt/services/scripts/export-env.sh

echo -n "[II] collecting staticfiles and starting django... "
bash /opt/services/AlertaDengue/runwsgi.sh
