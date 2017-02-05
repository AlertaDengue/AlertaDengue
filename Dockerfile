FROM debian:jessie

RUN apt-get update
RUN apt-get install -q -y locales python3 python3-pip python3-setuptools python3-numpy python3-pandas python3-shapely libpq-dev

# Set locale
RUN echo "pt_BR.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen pt_BR.UTF-8
RUN update-locale pt_BR.UTF-8
ENV LC_ALL pt_BR.UTF-8

# Create deploy user
RUN useradd --shell=/bin/bash --home=/srv/deploy/ --create-home deploy

# Send code to the container
ADD . /srv/deploy/AlertaDengue

WORKDIR /srv/deploy/AlertaDengue/AlertaDengue

# Install python deps
RUN pip3 install -r ../requirements.txt

# Collectstatic
RUN python3 manage.py collectstatic --noinput

RUN python3 manage.py migrate --run-syncdb --noinput

# Change the permissions for the user home directory
RUN chown -R deploy:deploy /srv/deploy/

EXPOSE 8000
USER deploy
CMD ["/srv/deploy/AlertaDengue/runwsgi.sh"]
