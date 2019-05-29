# Base

FROM ubuntu:18.04

# Install POSTGRESQL

RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ bionic-pgdg main"

RUN apt-get update && \
    apt-get install -q -y \
    postgresql-client \
    postgresql \
    postgresql-contrib \
    postgis

# Adjust PostgreSQL configuration so that remote connections to the database are possible.
RUN echo "host all  all    0.0.0.0/0  trust" >> /etc/postgresql/11/main/pg_hba.conf
# And add ``listen_addresses`` to ``postgresql.conf``
RUN echo "listen_addresses='*'" >> /etc/postgresql/11/main/postgresql.conf
EXPOSE 5432

# Set LOCALE

RUN echo "pt_BR.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen pt_BR.UTF-8
RUN update-locale pt_BR.UTF-8
ENV LC_ALL pt_BR.UTF-8
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Install PROGRAMS

RUN apt-get update && \
    apt-get install -q -y \
    locales \
    libpq-dev \
    wget \
    git \
    openssh-server \
    bzip2 \
    nano \
    sudo

# Create DENGUE USER

RUN useradd -s /bin/bash -g root -G sudo --home=/home/dengue/ --create-home dengue
RUN echo 'dengue:dengueadmin' | chpasswd
RUN echo '%dengue  ALL=(ALL:ALL) ALL' >> /etc/sudoers

# Change the permissions for the user home directory
RUN mkdir /home/dengue/logs
WORKDIR /home/dengue

# install MINICONDA

RUN wget -O ~/Miniconda.sh http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
RUN cd ~ && \
 bash Miniconda.sh -b -p /home/dengue/miniconda && \
 rm Miniconda.sh

#GIT clone alias DEVELOP
RUN git clone -b develop https://github.com/AlertaDengue/AlertaDengue.git

ENV PATH="/home/dengue/miniconda/bin:${PATH}"
 
ADD AlertaDengue/environment.yml /tmp/environment.yml
ADD AlertaDengue/requirements-dev.txt /tmp/requirements-dev.txt
RUN /home/dengue/miniconda/bin/conda config --add channels conda-forge
RUN /home/dengue/miniconda/bin/conda env update --file /tmp/environment.yml -n dengue36 python=3.6
RUN /home/dengue/miniconda/bin/conda install --file /tmp/requirements-dev.txt

# create SETTINGS file
RUN mv /home/dengue/AlertaDengue/ci/settings_DEMO.ini /home/dengue/AlertaDengue/AlertaDengue/AlertaDengue/settings.ini

# Git clone and restoreDB

RUN git clone https://github.com/AlertaDengue/Data.git --depth 1

RUN cd /home/dengue/Data && \
  ./restore.sh

