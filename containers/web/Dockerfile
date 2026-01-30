# ref: https://github.com/mamba-org/micromamba-docker/blob/main/Dockerfile
FROM condaforge/mambaforge:latest

LABEL maintainer="Sandro Loch <es.loch@gmail.com>"
LABEL org.opencontainers.image.title="AlertaDengue"
LABEL org.opencontainers.image.authors="AlertaDengue Team"
LABEL org.opencontainers.image.source="https://github.com/AlertaDengue/AlertaDengue"
LABEL org.opencontainers.image.version="latest"
LABEL org.opencontainers.image.description="AlertaDengue package"

USER root

ARG HOST_UID
ARG HOST_GID
ARG SERVICES
ARG ENV
ENV ENV_NAME=alertadengue
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -qq update --yes \
  && apt-get -qq install --yes --no-install-recommends curl \
  build-essential git make postgresql-client vim \
  ca-certificates wget locales cron sudo inotify-tools \
  libpq-dev pkg-config \
  && rm -rf /var/lib/apt/lists/* \
  /var/cache/apt/archives \
  /tmp/*

# Set locale
RUN sed -i -e "s/# pt_BR.*/pt_BR.UTF-8 UTF-8/" /etc/locale.gen \
  && dpkg-reconfigure --frontend=noninteractive locales \
  && update-locale LANG=pt_BR.UTF-8

# Create deploy user
RUN addgroup --gid ${HOST_GID} deploy \
  && useradd --uid ${HOST_UID} --gid ${HOST_GID} -ms /bin/bash deploy \
  && echo "deploy ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/deploy \
  && chmod 0440 /etc/sudoers.d/deploy \
  && export ENV_NAME="$ENV_NAME" \
  && mkdir -p /opt/conda /opt/services/ /tmp/dbf_parquet /opt/services/episcanner \
  && chown ${HOST_UID}:${HOST_GID} /opt/services/ /tmp/dbf_parquet \
  && chmod -R a+rwx /opt/conda /opt/services /tmp \
  && echo 'source activate "$ENV_NAME"' >  /home/deploy/.bashrc
ENV PATH "$PATH:/home/deploy/.local/bin"
ENV PATH /opt/conda/envs/$ENV_NAME/bin:$PATH

# Create script activate environment
RUN echo 'source /opt/conda/bin/activate alertadengue && exec "$@"' > /activate.sh
RUN chmod +x /activate.sh

USER deploy

SHELL ["/bin/bash", "-c"]

# --- Conda env ---
COPY --chown=${HOST_UID}:${HOST_GID} conda/base.yaml /tmp/environment.yaml
RUN conda env create -n $ENV_NAME \
  --file /tmp/environment.yaml \
  && conda clean --all \
  && find /opt/conda/ -type f,l -name '*.a' -delete \
  && find /opt/conda/ -type f,l -name '*.pyc' -delete \
  && find /opt/conda/ -type f,l -name '*.js.map' -delete

COPY --chown=${HOST_UID}:${HOST_GID} ./AlertaDengue  /opt/services/AlertaDengue
WORKDIR /opt/services/AlertaDengue

# Ensure Poetry installs venv inside the project and binaries are on PATH
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV POETRY_VIRTUALENVS_CREATE=true
ENV PATH="/opt/services/AlertaDengue/.venv/bin:${PATH}"

# Deps installer (uses conda/base.yaml via ENV_FILE)
COPY --chown=${HOST_UID}:${HOST_GID} ./scripts/install-deps.sh /tmp/install-deps.sh
COPY --chown=${HOST_UID}:${HOST_GID} .envs/.env.tpl pyproject.toml poetry.lock README.md ./
RUN ENV_FILE=/tmp/environment.yaml bash /tmp/install-deps.sh dev

# Runtime scripts
COPY --chown=${HOST_UID}:${HOST_GID} ./containers/scripts/crontab_setup.sh /opt/services/crontab_setup.sh
COPY --chown=${HOST_UID}:${HOST_GID} ./containers/scripts/cronjob /etc/cron.d/cronjob
COPY --chown=${HOST_UID}:${HOST_GID} ./containers/scripts/runcelery.sh  /opt/runcelery.sh
COPY --chown=${HOST_UID}:${HOST_GID} ./containers/scripts/runbeat.sh  /opt/runbeat.sh
COPY --chown=${HOST_UID}:${HOST_GID} ./containers/scripts/entrypoint.sh  /opt/entrypoint.sh
COPY --chown=${HOST_UID}:${HOST_GID} ./containers/scripts/runwsgi.sh /opt/runwsgi.sh
COPY --chown=${HOST_UID}:${HOST_GID} ./containers/scripts/test.sh /opt/services/test.sh

RUN chmod +x /opt/runwsgi.sh \
  && chmod +x /opt/entrypoint.sh \
  && chmod +x /opt/runcelery.sh \
  && chmod +x /opt/runbeat.sh \
  && printf '%s\n' \
     'if [ -f /opt/conda/etc/profile.d/conda.sh ]; then' \
     '  . /opt/conda/etc/profile.d/conda.sh' \
     '  conda activate alertadengue' \
     'fi' > /home/deploy/.bashrc

ENTRYPOINT ["tini", "--", "/opt/entrypoint.sh"]
CMD ["bash", "/opt/runwsgi.sh"]
