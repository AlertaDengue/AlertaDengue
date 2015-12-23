/**
 * This script provides data manipulation functions for infodengue.
 * Created by fccoelho on 22/10/15.
 */

//load geoJSON layers for use within a leaflet map
function load_map_layer(url, map) {
    $.getJSON(url, function (data) {
        geojson = L.geoJson(data, {
            style: style,
            onEachFeature: fill_popup
        });

        aps.addLayer(geojson, true);
        aps.addTo(map);
        features.addTo(map);
        map.fitBounds(geojson.getBounds())
    });
}

function fill_popup(feature, layer) {
    if ("COD_AP_SMS" in feature.properties) {
        codigo = parseFloat(feature.properties.COD_AP_SMS);
    } else {
        codigo = parseInt(feature.properties.geocodigo);
    }

    feature.properties.alerta = alerta[codigo];
    feature.properties.series = series_casos[codigo];
    feature.properties.casos = casos_por_ap[codigo];
    layer.bindPopup("<b>" + bairros[codigo] + "</b>" + "<br>" +
        "Casos: " + feature.properties.casos + "<br>Últimas semanas: <span class='inlinesparkline'>" +
        feature.properties.series + "</span><br>" +
        "<br><u>O que fazer</u>: " +
        recomendacoes[feature.properties.alerta]
    );
    layer.setStyle(style(feature))
    layer.on({
        mouseover: highlightFeature,
        mouseout: resetHighlight,
        popupopen: renderSparkline
    });

}

$(function () {

                var nd = new Date();
                var tzo = nd.getTimezoneOffset();
                // Agora as series de dados
                var dados = {{ dados|safe }};
                //$('#historico-chart-{{ ap }}').highcharts(
                var chart = new Highcharts.Chart(
                        {

                    chart: {
                        renderTo: "historico-chart",
                        zoomType: 'xy'
                    },
                    title: {
                        text: 'Séries de dados e Alertas anteriores para {{ ap }}'
                    },
                    subtitle: {
                        text: 'Fontes: SMS-RJ, Observatório da Dengue'
                    },
                    xAxis: [
                        {
                            type: 'datetime',
                            //categories: dados['{{ ap }}'].dia
                        }
                    ],
                    yAxis: [
                        { // Primary yAxis
                            labels: {
                                formatter: function () {
                                    return this.value + '°C';
                                },
                                style: {
                                    color: '#89A54E'
                                }
                            },
                            title: {
                                text: 'Temperatura',
                                style: {
                                    color: '#89A54E'
                                }
                            },
                            opposite: true

                        },
                        { // Secondary yAxis
                            gridLineWidth: 1,
                            type: "logarithmic",
                            title: {
                                text: 'Tweets',
                                style: {
                                    color: '#4572A7'
                                }
                            },
                            labels: {
                                formatter: function () {
                                    return this.value + ' tweets';
                                },
                                style: {
                                    color: '#4572A7'
                                }
                            }

                        },
                        { // Tertiary yAxis
                            gridLineWidth: 0,
                            type: "logarithmic",
                            title: {
                                text: 'Casos de Dengue',
                                style: {
                                    color: '#AA4643'
                                }
                            },
                            labels: {
                                formatter: function () {
                                    return this.value + ' pessoas';
                                },
                                style: {
                                    color: '#AA4643'
                                }
                            },
                            opposite: true
                        }
                    ],
                    tooltip: {
                        shared: true
                    },
                    legend: {
                        layout: 'vertical',
                        align: 'left',
                        x: 120,
                        verticalAlign: 'top',
                        y: 80,
                        floating: true,
                        backgroundColor: '#FFFFFF'
                    },
                    series: [
                        {
                            name: 'Temperatura',
                            color: '#89A54E',
                            yAxis: 0,
                            type: 'spline',
                            pointInterval: 7 * 24 * 3600 * 1000,
                            pointStart: {{ xvalues.0 }}*1000 + tzo,//Date.UTC(2009, 12, 27),
                            data: dados['{{ ap }}'].tmin,
                            tooltip: {
                                valueSuffix: ' °C'
                            }
                        },
                        {
                            name: 'Tweets',
                            type: 'spline',
                            color: '#4572A7',
                            pointInterval: 7 * 24 * 3600 * 1000,
                            pointStart: {{ xvalues.0 }}*1000 + tzo, //Date.UTC(2009, 12, 27),
                            yAxis: 1,
                            data: dados['{{ ap }}'].tweets,
                            marker: {
                                enabled: false
                            },
                            dashStyle: 'shortdot',
                            tooltip: {
                                valueSuffix: ' tweets'
                            }

                        },
                        {
                            name: 'Casos de Dengue',
                            color: '#AA4643',
                            type: 'line',
                            yAxis: 2,
                            pointInterval: 7 * 24 * 3600 * 1000,
                            pointStart: {{ xvalues.0 }}*1000 + tzo,//Date.UTC(2009, 12, 27),
                            data: dados['{{ ap }}'].casos_est,
                            tooltip: {
                                valueSuffix: ' pessoas'
                            }

                        }
                    ]
                });
            });
