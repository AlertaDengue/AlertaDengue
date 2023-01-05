# PostGIS
# ref: https://github.com/postgis/docker-postgis/blob/a6a9f021e243c0b6f908cf8ad8d0ae5460dcb1b1/14-3.2/initdb-postgis.sh

# Perform all actions as $POSTGRES_USER
export PGUSER="$POSTGRES_USER"

# Create the 'template_postgis' template db
"${psql[@]}" <<- 'EOSQL'
CREATE DATABASE template_postgis IS_TEMPLATE true;
EOSQL

# Load PostGIS into both template_database and $POSTGRES_DB
for DB in template_postgis "$PSQL_DBF"; do
	echo "Loading PostGIS extensions into $DB"
	"${psql[@]}" --dbname="$DB" <<-'EOSQL'
		CREATE EXTENSION IF NOT EXISTS postgis;
		CREATE EXTENSION IF NOT EXISTS postgis_topology;
		CREATE EXTENSION IF NOT EXISTS postgis_raster WITH SCHEMA public;
EOSQL

	if [ "$DB" = "$PSQL_DBF" ]; then
		echo "Adding PostGIS attributes to $DB"
		"${psql[@]}" --dbname="$PSQL_DBF" <<-'EOSQL'
			GRANT ALL ON TABLE public.geometry_columns TO PUBLIC;
			GRANT ALL ON TABLE public.spatial_ref_sys TO PUBLIC;
			GRANT ALL ON TABLE public.raster_columns TO PUBLIC;
			GRANT ALL ON TABLE public.raster_overviews TO PUBLIC;
		EOSQL
	fi

done
