#!/usr/bin/env bash

./docker-entrypoint-initdb.d/01-alter_password.sh
./docker-entrypoint-initdb.d/01-create_dengue_db.sh
./docker-entrypoint-initdb.d/01-create_infodengue_db.sh
