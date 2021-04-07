FROM continuumio/miniconda3

RUN apt-get -qq update --yes \
  && apt-get -qq install --yes --no-install-recommends \
  build-essential git make postgresql-client \
  ca-certificates wget locales cron \
  && rm -rf /var/lib/apt/lists/*

#Set locale
RUN sed -i -e "s/# pt_BR.*/pt_BR.UTF-8 UTF-8/" /etc/locale.gen \
  && dpkg-reconfigure --frontend=noninteractive locales \
  && update-locale LANG=pt_BR.UTF-8

# Configure conda-channels
RUN conda config --add channels conda-forge \
  && conda update --all --yes --quiet \
  && conda clean -afy

# Copy environment file to tmp/
ARG PYTHON_VERSION
COPY environment-${PYTHON_VERSION}.yml /tmp/environment.yml

# Use environment to update the env base
RUN conda env update --file /tmp/environment.yml --name base \
  && conda clean -afy

# Create deploy user
ARG HOST_UID
ARG HOST_GID
COPY docker/prepare_permission.sh /prepare_permission.sh
RUN /prepare_permission.sh

## Copy code to the container with permissions to user
# folders
COPY --chown=deploy:deploy docker  /srv/deploy/docker
COPY --chown=deploy:deploy AlertaDengue  /srv/deploy/AlertaDengue
# files
COPY --chown=deploy:deploy requirements.txt example_env_file /srv/deploy/

RUN cp -p /srv/deploy/example_env_file /srv/deploy/.env

RUN mkdir /srv/deploy/logs \
  && chown -R deploy:deploy /srv/deploy/logs

# Create script activate environment
RUN echo 'source /opt/conda/bin/activate base && exec "$@"' > activate.sh
RUN chmod +x /activate.sh
WORKDIR /srv/deploy/AlertaDengue

# Configure cron for DBF request
COPY docker/cron-sendmail /etc/cron.d/cron-sendmail
RUN chmod 0644 /etc/cron.d/cron-sendmail \
  && crontab -u deploy /etc/cron.d/cron-sendmail \
  && echo "deploy"  > /etc/cron.allow \
  && touch /var/log/cron.log \
  && chown deploy:deploy /var/log/cron.log

ADD docker/entrypoint.sh /entrypoint.sh

# USER deploy

ENTRYPOINT ["bash", "/activate.sh"]
CMD ["/entrypoint.sh", "/srv/deploy/AlertaDengue/runwsgi.sh"]
