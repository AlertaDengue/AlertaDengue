#!/bin/sh

exec envsubst < .env_episcanner.tpl > /opt/services/AlertaDengue/.env
