FROM debian:jessie

RUN apt-get update
RUN apt-get install -q -y locales git-core supervisor python3 python3-pip python3-setuptools python3-numpy python3-pandas python3-shapely libpq-dev memcached

# Set locale
RUN echo "pt_BR.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen pt_BR.UTF-8
RUN update-locale pt_BR.UTF-8
ENV LC_ALL pt_BR.UTF-8

# Configure Memcached
ADD config/memcached.conf /etc/supervisor/conf.d/memcached.conf

# Create deploy user
RUN useradd --shell=/bin/bash --home=/srv/deploy/ --create-home deploy
RUN mkdir -p /srv/deploy/logs/

# Send code to the container
ADD . /srv/deploy/AlertaDengue

# Install python deps
RUN pip3 install -r /srv/deploy/AlertaDengue/requirements.txt

# Collectstatic
RUN /srv/deploy/AlertaDengue/AlertaDengue/manage.py collectstatic --noinput

RUN /srv/deploy/AlertaDengue/AlertaDengue/manage.py migrate --run-syncdb --noinput

# Configure supervisor job
ADD config/alerta_dengue.conf /etc/supervisor/conf.d/alerta_dengue.conf

# Change the permissions for the user home directory
RUN chown -R deploy:deploy /srv/deploy/

EXPOSE 8000
CMD ["/usr/bin/supervisord", "--nodaemon"]
