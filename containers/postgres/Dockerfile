# from https://github.com/postgis/docker-postgis/blob/969ef8a9e4a22e1556ca99cab4178f6e60c1483d/14-3.2/Dockerfile
FROM postgres:14-bullseye

LABEL maintainer="Sandro Loch <es.loch@gmail.com>"

ENV PG_MAJOR 14
ENV POSTGIS_MAJOR 3

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
      postgresql-plpython3-14 \
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
