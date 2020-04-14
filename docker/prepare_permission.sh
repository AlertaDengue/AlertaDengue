#!/bin/bash

# Basic if statement
if [[ ${HOST_UID} != 0 ]]
then
groupadd --gid ${HOST_GID} celery # we need the same GID as the host.
useradd --shell=/bin/bash --home=/srv/deploy/ --create-home deploy -u ${HOST_UID} -g ${HOST_GID}
else
  RUN useradd --shell=/bin/bash --home=/srv/deploy/ --create-home deploy
fi
