#!/bin/bash

# Basic if statement
if [-z ${HOST_UID}]
  then
    RUN useradd --shell=/bin/bash --home=/srv/deploy/ --create-home deploy
  else
    groupadd --gid ${HOST_GID} deploy # we need the same GID as the host.
    useradd --shell=/bin/bash --home=/srv/deploy/ --create-home deploy -u ${HOST_UID} -g ${HOST_GID}
fi;
