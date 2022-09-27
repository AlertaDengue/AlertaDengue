FROM mdillon/postgis:9.6

# import the schemas for testing
# ADD docker/postgres/schema/* /docker-entrypoint-initdb.d/

# Dump dump for development
COPY docker/postgres/schema/* /docker-entrypoint-initdb.d/
