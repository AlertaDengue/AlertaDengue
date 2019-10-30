#!/usr/bin/env bash
echo "[II] Starting entrypoint scripts ..."
echo "[II] postgis.sh ..."
# . /docker-entrypoint-initdb.d/postgis.sh
echo "[II] 01-alter_password.sh ..."
# . /docker-entrypoint-initdb.d/01-alter_password.sh
echo "[II] 01-create_dengue_db.sh ..."
# . /docker-entrypoint-initdb.d/01-create_dengue_db.sh
echo "[II] 01-create_infodengue_db.sh ..."
# . /docker-entrypoint-initdb.d/01-create_infodengue_db.sh
echo "[II] done."
