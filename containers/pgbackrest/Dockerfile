FROM postgres:14-bullseye

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    pgbackrest \
    ca-certificates \
    bash \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p \
    /etc/pgbackrest \
    /var/lib/pgbackrest \
    /var/lib/pgbackrest/spool \
    /var/log/pgbackrest \
    /var/run/postgresql

CMD ["bash", "-lc", "sleep infinity"]
