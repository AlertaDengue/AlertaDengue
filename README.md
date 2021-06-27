# AlertaDengue
Portal de dados do Projeto Alerta Dengue / Portal de Datos del Proyecto Alerta Dengue

## Como Contribuir?
Para criar um ambiente desenvolvimento é necessário: / PAra crear o tener un ambiente de desarrollo es necesario:
 1. Crie um virtualenv; / Crear un virtualenv (entorno virtual);
 2. Instale as dependencias do projeto; / Instalar las dependencias del proyecto;
 3. Crie o banco de dados local; / Crear o tener una base de datos local;
 4. Crie um arquivo settings.ini baseado no exemplo. / Armar un archivo de configuracion o settings.ini basado en el ejemplo.

Se já possuir o [virtualenvwrapper](https://pypi.python.org/pypi/virtualenvwrapper) instalado, esse passo-a-passo pode ser feito através dos comandos:
```bash
$ mkvirtualenv AlertaDengue -r requirements.txt
$ python AlertaDengue/manage.py syncdb
$ cp AlertaDengue/{example-,}settings.ini
```

## Formato dos mapas

O site requer dados na projeção EPSG:4326
para converter de SAD69 para EPSG:4326 (lat,lon) use o seguinte comando:

```bash
ogr2ogr -t_srs EPSG:4326 -a_srs EPSG:4326 Dengue_2010_latlon.shp Dengue2010_BancoSINAN16_04_2012_v09012014.shp
```
o primeiro shape é o arquivo convertido que será criado e o segundo o arquivo de origem.

##Geração dos modelos do banco para dados a ser importados de shapefiles

rode:

```
./manage.py ogrinspect --mapping <nome do shape>
```

copie a saída deste comando para models.py

então modifique o script load.py para importar do shapefile os dados para o Banco do aplicativo Django.

## Configurar ambiente de desenvolvimento

Em ambiente de desenvolvimento o Alerta Dengue será instalado e irá instalar um hook de pre-commit que irá analisar a formatação dos códigos python usando o flake8 antes de efetivar qualquer comando commit.

rode:
```
make develop
````
