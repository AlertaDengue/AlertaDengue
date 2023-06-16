#!/usr/bin/env bash
current_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd ${current_dir}/AlertaDengue;
env_file=".env" manage.py test ${1}
