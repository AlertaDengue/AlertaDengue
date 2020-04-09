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

ARG PYTHON_VERSION
COPY environment-${PYTHON_VERSION}.yml /tmp/environment.yml

RUN /opt/conda/bin/conda config --add channels conda-forge \
  && /opt/conda/bin/conda update --all --yes --quiet \
  && /opt/conda/bin/conda env update --name base --file /tmp/environment.yml \
  && /opt/conda/bin/conda install --yes conda-build \
  && /opt/conda/bin/conda clean --all --yes

ENV PATH="/opt/conda/bin:${PATH}"

# copy code to the container
# Change the permissions for the user home directory
RUN mkdir /srv/deploy/logs
COPY --chown=deploy AlertaDengue  /srv/deploy/AlertaDengue

WORKDIR /srv/deploy/AlertaDengue

EXPOSE 8000
USER deploy
CMD ["/srv/deploy/AlertaDengue/runwsgi.sh"]
