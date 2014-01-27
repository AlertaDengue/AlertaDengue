#AlertaDengue


Portal de dados do Projeto Alerta Dengue


##Formato dos mapas

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