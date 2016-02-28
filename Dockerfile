FROM debian

# Install system packages
# the 'debian' base image is having problems with the repositories, so we'll just use the one we know is working.
ADD config/sources.list /etc/apt/sources.list

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update
#RUN apt-get install -y locales nginx sqlite3 libspatialite3 spatialite-bin git-core supervisor python3 python3-pip python3-setuptools python-virtualenv openssh-server
RUN apt-get install -y locales nginx sqlite3 libspatialite5 spatialite-bin git-core supervisor python3 python3-pip python3-setuptools python-virtualenv python3-venv openssh-server python3-numpy python3-pandas python3-shapely postgresql libpq-dev memcached

# Set locale
RUN echo "pt_BR.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen pt_BR.UTF-8
RUN update-locale pt_BR.UTF-8
ENV LC_ALL pt_BR.UTF-8

# Configure SSHd
#TODO: Add config file with sane configs (only publickey auth, etc) and keys
RUN mkdir -p /var/run/sshd
# https://stackoverflow.com/questions/18173889/cannot-access-centos-sshd-on-docker/18374381#18374381
RUN sed -ri 's/UsePAM yes/#UsePAM yes/g' /etc/ssh/sshd_config
ADD config/sshd.conf /etc/supervisor/conf.d/sshd.conf

# Configure nginx
ADD config/nginx.conf /etc/supervisor/conf.d/nginx.conf
RUN rm /etc/nginx/sites-enabled/default
RUN echo "daemon off;" >> /etc/nginx/nginx.conf

# Configure Memcached
ADD config/memcached.conf /etc/supervisor/conf.d/memcached.conf

# Create deploy user
RUN useradd --shell=/bin/bash --home=/srv/deploy/ --create-home deploy
RUN mkdir -p /srv/deploy/logs/

# Configure virtualenv
RUN pyvenv --clear --system-site-packages /srv/deploy/project/
ADD exec_in_virtualenv.sh /srv/deploy/exec_in_virtualenv.sh

# Clone code
RUN git clone https://github.com/AlertaDengue/AlertaDengue.git /srv/deploy/project/AlertaDengue

# Add our local settings. This file is not versioned because it contains
# sensitive data (such as the SECRET_KEY).
ADD AlertaDengue/AlertaDengue/settings.ini /srv/deploy/project/AlertaDengue/AlertaDengue/AlertaDengue/settings.ini

# Install python deps
# We need --no-clean because of the way Docker.io's filesystem works. When pip
# tries to remove the build directory, it raises an error, saying the file was
# not found. After the RUN command finishes (it was commited), removing the
# directory works fine.
RUN /srv/deploy/exec_in_virtualenv.sh pip3 install --no-clean -r /srv/deploy/project/AlertaDengue/requirements.txt
RUN rm -r /tmp/pip_build_root/

# Collectstatic
RUN /srv/deploy/exec_in_virtualenv.sh /srv/deploy/project/AlertaDengue/AlertaDengue/manage.py collectstatic --noinput

# Configure supervisor job
ADD config/alerta_dengue.conf /etc/supervisor/conf.d/alerta_dengue.conf

# Configure nginx
ADD config/alerta_dengue_nginx.conf /etc/nginx/sites-enabled/alerta_dengue

# Copy ssh keys
RUN mkdir /root/.ssh/
ADD authorized_keys /root/.ssh/authorized_keys

RUN mkdir /srv/deploy/.ssh/
ADD authorized_keys /srv/deploy/.ssh/authorized_keys

# Change the permissions for the user home directory
RUN chown -R deploy:deploy /srv/deploy/

EXPOSE 22 80
CMD ["/usr/bin/supervisord", "--nodaemon"]
