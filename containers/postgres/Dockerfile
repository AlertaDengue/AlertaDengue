# PostgreSQL 18 uses the official Bookworm image with matching PostGIS packages.
FROM postgres:18.6-bookworm

LABEL maintainer="Sandro Loch <es.loch@gmail.com>"

ENV PG_MAJOR=18
ENV PGDATA=/var/lib/postgresql/18/docker
ENV POSTGIS_MAJOR=3

ARG HOST_UID
ARG HOST_GID

RUN usermod -u ${HOST_UID} postgres \
    && groupmod -g ${HOST_GID} postgres \
    && echo "postgres:x:${HOST_UID}:${HOST_GID}:PostgreSQL,,,:/var/lib/postgresql:/bin/bash" >> /etc/passwd \
    && chown -R ${HOST_UID}:${HOST_GID} /var/run/postgresql \
    && chown -R ${HOST_UID}:${HOST_GID} /var/lib/postgresql

RUN apt-get update \
      && apt-cache showpkg postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR \
      && apt-get install -y --no-install-recommends \
      python3 \
      postgresql-plpython3-18 \
      postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR \
      postgresql-$PG_MAJOR-postgis-$POSTGIS_MAJOR-scripts \
      pgbackrest \
      && rm -rf /var/lib/apt/lists/*

RUN mkdir -p \
      /etc/pgbackrest \
      /var/lib/pgbackrest \
      /var/lib/pgbackrest/spool \
      /var/log/pgbackrest \
      /backups \
 && chown -R ${HOST_UID}:${HOST_GID} \
      /etc/pgbackrest \
      /var/lib/pgbackrest \
      /var/lib/pgbackrest/spool \
      /var/log/pgbackrest \
      /backups

COPY containers/postgres/scripts/entrypoint.sh /usr/local/bin/pg-entrypoint
COPY containers/pgbackrest/wait_for_postgres.sh /usr/local/bin/wait-for-postgres
RUN chmod +x /usr/local/bin/pg-entrypoint /usr/local/bin/wait-for-postgres

ENTRYPOINT ["pg-entrypoint"]
CMD ["postgres"]
