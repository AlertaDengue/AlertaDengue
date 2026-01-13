#!/usr/bin/env bash

set -ex

# prepare the conda environment
is_conda_in_path=$(echo "$PATH" | grep -m 1 --count /opt/conda/)

if [ "$is_conda_in_path" == 0 ]; then
  export PATH="/opt/conda/condabin:/opt/conda/bin:$PATH"
  echo "[INFO] included conda to the PATH"
fi

echo "[INFO] activate alertadengue"
. /opt/conda/etc/profile.d/conda.sh
conda activate alertadengue

set +ex

if [ "$#" -ne 0 ]; then
  echo "Running: $*"
  exec "$@"
fi
