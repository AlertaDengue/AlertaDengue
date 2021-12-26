Deploying to a staging environment
----------------------------------

You will need a fresh dump of the development environment on
./dev_dumps/ (in the root directory of the repository). You also need
to set the following environment variables in your local `.env` file
(along with all the other ones that were already set):

* `PSQL_PASSWORD`
* `PSQL_USER`
* `PSQL_HOST=staging_db` - you need this value for `PSQL_HOST` as it will be the hostname for the database container
* `STAGING_DATA_DIR` - this is where the db container will keep the postgres data directory


After that, all you need to do is `make deploy_staging` and
docker-compose will build all the images and run them.
