FROM debian:testing

# RUN apt-get update && apt-get install -q -y locales python3 python3-pip python3-setuptools python3-numpy python3-pandas libpq-dev python3-gdal libgdal-dev python3-geopandas
RUN apt-get update && \
    apt-get install -q -y locales \
      python3 \
      python3-pip \
      python3-setuptools \
      libpq-dev \
      libgdal-dev \
      wget

# Set locale
RUN echo "pt_BR.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen pt_BR.UTF-8
RUN update-locale pt_BR.UTF-8
ENV LC_ALL pt_BR.UTF-8
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Create deploy user
RUN useradd --shell=/bin/bash --home=/srv/deploy/ --create-home deploy

# install miniconda
RUN wget -O Miniconda.sh http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh

RUN bash Miniconda.sh -b -p /opt/miniconda && \
    rm Miniconda.sh

ENV PATH="/opt/miniconda/bin:${PATH}"

# config conda
RUN conda config --set show_channel_urls True && \
    conda update --yes --all && \
    conda clean --tarballs --packages && \
    conda config --add channels conda-forge

ADD AlertaDengue/requirements-conda.txt /tmp/requirements-conda.txt
RUN conda install --file /tmp/requirements-conda.txt

# Send code to the container
ADD AlertaDengue /srv/deploy/AlertaDengue

# Change the permissions for the user home directory
RUN mkdir /srv/deploy/logs
RUN chown -R deploy:deploy /srv/deploy/

WORKDIR /srv/deploy/AlertaDengue

EXPOSE 8000
USER deploy
CMD ["/srv/deploy/AlertaDengue/runwsgi.sh"]
