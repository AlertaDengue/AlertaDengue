#!/bin/bash
exec celery -A ad_main worker -l INFO
