#!/usr/bin/env bash

# prepare the conda environment
is_conda_in_path=$(echo $PATH|grep -m 1 --count /opt/conda/)

if [ $is_conda_in_path == 0 ]; then
  export PATH="/opt/conda/condabin:/opt/conda/bin:$PATH"
  echo "[II] included conda to the PATH"
fi

echo -n "[II] activating arx ... "
source activate arx
echo "OK"

if [ $# -ne 0 ]
  then
    echo "Running: ${@}"
    ${@}
fi
