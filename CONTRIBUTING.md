# AlertaDengue: Developing Info Dengue

## Ubuntu Operating System

Mount the environment using the conda package manager and Python 3

## Miniconda3

Download:

 ```sh
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh
 ```

 Install:

```sh
chmod +x ~/miniconda.sh
cd ~
./miniconda.sh
export PATH=~/miniconda3/bin:$PATH
```

Add channel:

```sh
conda config --add channels conda-forge
```

update:

```sh
conda update conda
```

## Info Dengue

Download the app:

```sh
cd ~
git clone https://github.com/AlertaDengue/AlertaDengue.git
```

Create the virtual env and install the packages needed to run the application:

```sh
conda env create python=3.7 -f ~/AlertaDengue/AlertaDengue/AlertaDengue/environment.yml
```

Enable a virtual env "alertadengue":

```sh
conda activate alertadengue
```

Installs the archive packages "requirements-dev.txt":

```sh
conda install -f ~/AlertaDengue/AlertaDengue/AlertaDengue/requirements-dev.txt
```

Creates the settings file: 

```sh
nano ~/AlertaDengue/AlertaDengue/AlertaDengue/AlertaDengue/settings.ini
```

    Consider your local setting. Example:

    ```sh
    [settings]
    ALLOWED_HOSTS=alerta.dengue.mat.br,info.dengue.mat.br,*
    SECRET_KEY=my-secret-key
    DEBUG=True

    DATABASE_URL=postgres://dengueadmin:dengueadmin@localhost:5432/infodengue

    PSQL_DB = dengue
    PSQL_PASSWORD = dengueadmin
    PSQL_HOST = localhost

    ADMIN=''
    CELERY_BROKER_URL = amqp://xmn:xmn@192.168.1.3:5672
    CELERY_TASK_ALWAYS_EAGER = True

    MAPSERVER_URL = http://172.17.0.2:80
    MAPFILE_PATH = /var/www/mapserver/mapfiles
    RASTER_PATH = /var/www/mapserver/tiffs

    MAPBOX_TOKEN = pk.eyJ1IjoieG1ubGFiIiwiYSI6ImNqZHhrNmcxbDBuZnUyd28xYTg5emVoeTcifQ.9CMl24WjXQ4iThxYYoc3XA
    ```

Install the location packages:

```sh
apt install -y locales && locale-gen pt_BR.UTF-8
update-locale LANG=pt_BR.UTF-8
```

Access the application directory:

```sh
cd ~/AlertaDengue/AlertaDengue/
```

Synchronize geographic files:

```sh
python AlertaDengue/manage.py sync_geofiles
```

Generates the migration files:

```sh
python AlertaDengue/manage.py makemigrations
```

Performs migrations in the database:

```sh
python AlertaDengue/manage.py migrate
```

Test the applications: dados, api, gis, dbf e forecast

```sh
python AlertaDengue/manage.py test dados
python AlertaDengue/manage.py test api
python AlertaDengue/manage.py test gis
python AlertaDengue/manage.py test dbf
python AlertaDengue/manage.py test forecast
```

Run the application server:

```sh
python AlertaDengue/manage.py runserver
```
