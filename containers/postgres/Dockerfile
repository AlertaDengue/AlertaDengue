FROM mdillon/postgis:9.6

# import the schemas for testing
# ADD containers/postgres/schema/* /docker-entrypoint-initdb.d/

# Dump dump for development
ADD containers/postgres/schema/* /docker-entrypoint-initdb.d/
