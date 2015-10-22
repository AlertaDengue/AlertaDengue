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
