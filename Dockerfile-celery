FROM debian:testing

RUN apt-get update && apt-get install -q -y python3 python3-pip python3-setuptools python3-numpy python3-pandas libpq-dev python3-gdal libgdal-dev python3-geopandas

# Create deploy user
RUN useradd --shell=/bin/bash --home=/srv/deploy/ --create-home deploy


RUN mkdir /IMPORTED_FILES/
RUN chown -R deploy:deploy /IMPORTED_FILES/

# Add and install requirements.txt before we send the code so we don't have to
# install everything again whenever any file in this directory changes (this
# helps build the container a *lot* faster by using the cache.
ADD AlertaDengue/requirements.txt /tmp/requirements.txt

RUN pip3 install -r /tmp/requirements.txt

# Send code to the container
ADD AlertaDengue /srv/deploy/AlertaDengue

WORKDIR /srv/deploy/AlertaDengue

# Change the permissions for the user home directory
RUN chown -R deploy:deploy /srv/deploy/

RUN pip3 install celery

USER deploy

CMD ["/srv/deploy/AlertaDengue/run_celery_worker.sh"]
