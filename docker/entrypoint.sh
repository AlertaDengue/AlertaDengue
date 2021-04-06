#!/bin/bash
echo "Executing the entrypoint!"
echo "Force crond start"
service cron restart
echo "executing $@"
$@
