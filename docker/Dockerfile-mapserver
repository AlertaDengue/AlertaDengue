FROM geodata/mapserver

RUN apt-get update && \
    apt-get install locales && \
    apt-get clean

# Set locale
RUN echo "pt_BR.UTF-8 UTF-8" > /etc/locale.gen
RUN locale-gen pt_BR.UTF-8
RUN update-locale pt_BR.UTF-8
ENV LC_ALL pt_BR.UTF-8

RUN touch /var/log/mapserver.log && \
    chown www-data /var/log/mapserver.log

EXPOSE 80
