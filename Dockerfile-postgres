FROM postgres:9.6

RUN apt-get update && apt-get install -q -y postgresql-9.6-postgis-scripts

ADD postgres_setup /docker-entrypoint-initdb.d
ADD dev_dumps /dumps
ADD sql /docker-entrypoint-sql
