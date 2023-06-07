#!/usr/bin/env bash

echo "[INFO] Starting celery..."
celery \
  --app=ad_main.celeryapp:app \
  worker -Ofair -l INFO
