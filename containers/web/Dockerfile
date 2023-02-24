# ref: https://github.com/mamba-org/micromamba-docker/blob/main/Dockerfile
FROM condaforge/mambaforge:latest

LABEL maintainer="Sandro Loch <es.loch@gmail.com>"
LABEL org.opencontainers.image.title="AlertaDengue"
LABEL org.opencontainers.image.authors="AlertaDengue Team"
LABEL org.opencontainers.image.source="https://github.com/AlertaDengue/AlertaDengue"
LABEL org.opencontainers.image.version="latest"
LABEL org.opencontainers.image.description="AlertaDengue package"

# it is the default, but using it here to have it explicitly
USER root

SHELL ["/bin/bash", "-c"]
# Use bash in Dockerfile RUN commands and make sure bashrc is sourced when
# executing commands with /bin/bash -c
# Needed to have the micromamba activate command configured etc.

ARG HOST_UID
ARG HOST_GID
ARG SERVICES
ARG ENV
ENV ENV_NAME=alertadengue
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -qq update --yes \
  && apt-get -qq install --yes --no-install-recommends \
    build-essential git make postgresql-client vim \
    ca-certificates wget locales cron sudo \
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
  && mkdir -p /opt/conda /opt/services/ \
  && chmod -R a+rwx /opt/conda /opt/services /tmp \
  && chown deploy:deploy /opt/services/ /tmp \
  && echo 'source activate "$ENV_NAME"' >  /home/deploy/.bashrc \
  && printenv | sed 's/^\(.*\)$/export \1/g' >> /preload.sh

ENV PATH "$PATH:/home/deploy/.local/bin"
ENV PATH /opt/conda/envs/$ENV_NAME/bin:$PATH

USER deploy

# Copy code to the container with permissions to user
COPY --chown=deploy:deploy AlertaDengue  /opt/services/AlertaDengue
COPY --chown=deploy:deploy .env_default.tpl pyproject.toml README.md /opt/services/
COPY --chown=deploy:deploy conda/"${ENV}".yaml /tmp/environment.yaml
COPY --chown=deploy:deploy containers/celery/run.sh  /opt/services/celery-run.sh
COPY --chown=deploy:deploy containers/entrypoint.sh  /entrypoint.sh

# Change shell to bash
SHELL ["/bin/bash", "-c"]

# Use environment to update the env alertadengue
RUN mamba env create -n $ENV_NAME \
    --file /tmp/environment.yaml \
  && mamba clean --all \
  && find /opt/conda/ -type f,l -name '*.a' -delete \
  && find /opt/conda/ -type f,l -name '*.pyc' -delete \
  && find /opt/conda/ -type f,l -name '*.js.map' -delete
  # && rm -rf /home/deploy/.conda/pkgs

COPY --chown=deploy:deploy containers/scripts/poetry-install.sh /tmp/poetry-install.sh

WORKDIR /opt/services/AlertaDengue

RUN bash /tmp/poetry-install.sh

ENTRYPOINT ["bash", "/entrypoint.sh"]
