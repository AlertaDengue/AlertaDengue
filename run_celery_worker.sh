#!/bin/bash
exec celery -A AlertaDengue worker -l info
