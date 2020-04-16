FROM continuumio/miniconda3

RUN apt-get -qq update --yes \
 && apt-get -qq install --yes --no-install-recommends \
    build-essential git make postgresql-client \
    ca-certificates wget locales \
 && rm -rf /var/lib/apt/lists/*

#Set locale
RUN sed -i -e "s/# pt_BR.*/pt_BR.UTF-8 UTF-8/" /etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales \
    && update-locale LANG=pt_BR.UTF-8

# Create deploy user
RUN useradd --shell=/bin/bash --home=/srv/deploy/ --create-home deploy

# Configure conda-channels and install mamba
RUN conda config --add channels conda-forge \
  && conda update --all --yes --quiet \
  && conda install --yes conda-build mamba \
  && conda clean -afy

# Copy environment file to tmp/
ARG PYTHON_VERSION
COPY environment-${PYTHON_VERSION}.yml /tmp/environment.yml

# Use environment to update the env base
RUN mamba env update --file /tmp/environment.yml --name base \
  && conda clean -afy

# Copy AlertaDengue into home directory and fix permissions
RUN mkdir /srv/deploy/logs
COPY --chown=deploy AlertaDengue  /srv/deploy/AlertaDengue

WORKDIR /srv/deploy/AlertaDengue

EXPOSE 8000
USER deploy

CMD ["/srv/deploy/AlertaDengue/runwsgi.sh"]
