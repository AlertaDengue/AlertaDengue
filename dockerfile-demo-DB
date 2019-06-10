# Base

FROM debian:latest

# Install 

RUN apt-get update && \
    apt-get install -q -y \
    locales \
    wget \
    git \
    openssh-server \
    bzip2 \
    curl \
    libpq-dev \
    nano \
    sudo

# Set LOCALE

RUN echo "pt_BR.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen pt_BR.UTF-8
RUN update-locale pt_BR.UTF-8
ENV LC_ALL pt_BR.UTF-8
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Instal repo git lfs

#RUN echo 'deb http://http.debian.net/debian wheezy-backports main' > /etc/apt/sources.list.d/wheezy-backports-main.list
RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
RUN apt-get install git-lfs

# Install POSTGRESQL

RUN apt-get update && \
    apt-get install -q -y \
    postgresql \
    postgresql-contrib \
    postgis

# Create DENGUE USER

RUN useradd -s /bin/bash -g root -G sudo --home=/home/dengue/ --create-home dengue
RUN echo 'dengue:dengueadmin' | chpasswd
RUN echo '%dengue  ALL=(ALL:ALL) ALL' >> /etc/sudoers
USER dengue

# Change the permissions for the user home directory
RUN mkdir /home/dengue/logs
WORKDIR /home/dengue

#RUN pg_ctl -D /home/postgresql/9.6/bdata -l start
RUN PATH=/usr/lib/postgresql/9.6/bin:$PATH
RUN /usr/lib/postgresql/9.6/bin/initdb -E utf8 -D /home/dengue/bdata 

USER root
# Adjust PostgreSQL configuration so that remote connections to the database are possible.
RUN echo "host     all             all             0.0.0.0/0               md5" >> /etc/postgresql/9.6/main/pg_hba.conf
# And add ``listen_addresses`` to ``postgresql.conf``
RUN sed -i -e"s/^#listen_addresses =.*$/listen_addresses = '*'/" /etc/postgresql/9.6/main/pg_hba.conf
EXPOSE 5432

# install MINICONDA

RUN wget -O ~/Miniconda.sh http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
RUN cd ~ && \
 bash Miniconda.sh -b -p /home/dengue/miniconda && \
 rm Miniconda.sh

#GIT clone alias DEVELOP
RUN git clone -b develop https://github.com/AlertaDengue/AlertaDengue.git

ENV PATH="/home/dengue/miniconda/bin:${PATH}"
RUN /home/dengue/miniconda/bin/conda config --add channels conda-forge
RUN /home/dengue/miniconda/bin/conda env update --file /tmp/environment.yml -n dengue36 python=3.6
RUN /home/dengue/miniconda/bin/conda install --file /tmp/requirements-dev.txt

# create SETTINGS file
RUN mv /home/dengue/AlertaDengue/ci/settings-demo.ini /home/dengue/AlertaDengue/AlertaDengue/AlertaDengue/settings.ini

# Git clone and restoreDB
RUN git lfs install
RUN git lfs clone https://github.com/AlertaDengue/Data.git --depth 1
USER postgres
WORKDIR /home/dengue/Data
RUN cd /home/dengue/Data && \
   ./restore.sh
USER root