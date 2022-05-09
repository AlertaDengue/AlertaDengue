# InfoDengue
## _InfoDengue is an arboviruses alert system to every city of Brazil, the system is based on hybrid data generated through the analysis of climate and epidemiological data and social scraping_


For more information, please visit our website [info.dengue.mat.br](https://info.dengue.mat.br) to visualize the current epidemiological situation in each state.

---

### Check out below the softwares we use in the project:

| <a href=https://www.djangoproject.com/><img width="210" height="100" alt="Django" src="https://i.imgur.com/Z9wo3bS.png"></a> | <img width="210" height="100" alt="postgis" src="https://i.imgur.com/pVEX2Gl.png">|<img width="210" height="100" alt="docker" src="https://i.ibb.co/Yp8B38R/docker.png"> |
|:-------------------------:|:-------------------------:|:-------------------------:|
|<img width="210" height="100" alt="celery" src="https://i.ibb.co/L81p2zD/celery.png"> |  <img width="210" height="100" alt="nginx" src="https://i.ibb.co/2n5HZBg/nginx.png">|<img width="210" alt="plotly" src="https://i.ibb.co/r0HYsYH/plotly.png">|

---

## How to contribute with InfoDengue

You can find more information about [Contributing](https://github.com/AlertaDengue/AlertaDengue/blob/main/CONTRIBUTING.md) on GitHub. Also check our [Team](https://info.dengue.mat.br/equipe/) page to see if there is a work oportunity in the project.

---
## How data can be visualized 

The Infodengue website is accessed by many people and it is common for us to receive news that this information is used in the definition of travel and other activities. All data is compiled, analyzed and generated in a national level with the support of the Brazilian Health Ministry, the weekly reports can be found in our website through graphics or downloaded in JSON and CSV files via [API](https://info.dengue.mat.br/services/api).  


### API

The InfoDengue API will provide the data contained in the reports compiled in JSON or CSV files, it also provides a custom range of time. _If you don't know Python or R, please check the tutorials [here](https://info.dengue.mat.br/services/tutorial)._

### Reports

If you are a member of a Municipal Health Department, or a citizen, and you have interest in detailed information on the transmission alerts of your municipality, just type the name of the city or state [here](https://info.dengue.mat.br/report/).

---

## Where the data comes from 
- Dengue, Chikungunya and Zika data are provided by [SINAN](http://portalsinan.saude.gov.br/) as a notification form that feeds a municipal database, which is then consolidated at the state level and finally, federally by the Ministry of Health. Only a fraction of these cases are laboratory confirmed, most receive final classification based on clinical and epidemiological criteria. From the notified cases, the incidence indicators that feed the InfoDengue are calculated.
- InfoDengue has partnered with the [Dengue Observatory](https://www.observatorio.inweb.org.br/), that captures and analyzes tweets from geolocalized people for the mention of dengue symptoms on social media.
- Weather and climate data are obtained from [REDEMET](https://www.redemet.aer.mil.br/) in the airports all over Brazil.
- Epidemiological indicators require population size. Demographic data of Brazilian cities are updated each year in Infodengue using estimates [IBGE](https://www.ibge.gov.br/pt/inicio.html).

---

### Sponsors

<div style="width: 100%; text-align: left; position: relative;">
  <div style="display: inline-block;">
    <a href="https://portal.fiocruz.br/"> <img width="210" alt="Fiocruz" src="https://institutolula.org/uploads/6862.png" />
  </div>
  <div style="position: absolute; right: 0; top: 0">
    <a href="https://emap.fgv.br/"> <img src="https://bibliotecadigital.fgv.br/dspace/bitstream/id/329f55c1-0ed0-4a52-b8ef-1e250f60014a/?sequence=-1" alt="FGV EMAp" />
  </div>
</div>

---
