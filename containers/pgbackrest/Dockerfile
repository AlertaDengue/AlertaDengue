FROM postgres:14-bullseye

ARG HOST_UID
ARG HOST_GID

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    pgbackrest \
    ca-certificates \
    bash \
  && rm -rf /var/lib/apt/lists/*

RUN usermod -u ${HOST_UID} postgres \
  && groupmod -g ${HOST_GID} postgres \
  && chown -R ${HOST_UID}:${HOST_GID} \
    /var/lib/postgresql \
    /var/run/postgresql

RUN mkdir -p \
    /etc/pgbackrest \
    /var/lib/pgbackrest \
    /var/lib/pgbackrest/spool \
    /var/log/pgbackrest \
    /var/run/postgresql \
  && chown -R ${HOST_UID}:${HOST_GID} \
    /etc/pgbackrest \
    /var/lib/pgbackrest \
    /var/lib/pgbackrest/spool \
    /var/log/pgbackrest \
    /var/run/postgresql

USER postgres

CMD ["bash", "-lc", "sleep infinity"]
