/**
 * This script provides data manipulation functions for infodengue.
 * Created by fccoelho on 22/10/15.
 */

//load geoJSON layers for use within a leaflet map
function load_map_layer(urls, map) {
  const boundsGroup = L.featureGroup();

  urls.forEach(function(url) {
    $.getJSON(url, function(data) {
      const focus = url.includes(geocode);
      const geojson = L.geoJson(data, {
        style: feature => style(feature, focus),
        onEachFeature: (feature, layer) => {
          fill_popup(feature, layer);
          if (focus) {
            focused_layer = layer;
          }
        }
      });

      aps.addLayer(geojson, true);
      aps.addTo(map);
      features.addTo(map);
      boundsGroup.addLayer(geojson);

      if (boundsGroup.getLayers().length === urls.length) {
        map.fitBounds(boundsGroup.getBounds());
      }
    });
  });

  if (focused_layer) {
    focused_layer.bringToFront();
  }
}

function fill_popup(feature, layer) {
  if ("COD_AP_SMS" in feature.properties) {
    codigo = parseFloat(feature.properties.COD_AP_SMS);
  } else {
    codigo = parseInt(feature.properties.geocodigo);
  }
  const focus = String(codigo) === String(geocode);

  const url = new URL(window.location.href);
  const segs = url.pathname.split('/');
  segs[2] = codigo;

  feature.properties.name = bairros[codigo];
  feature.properties.alerta = alerta[codigo];
  feature.properties.series = series_casos[codigo];
  feature.properties.casos = casos_por_ap[codigo];

  const sparkId = `spark-${codigo}`;

  layer.bindPopup(
    `<div style="padding: 0 10px; box-sizing: border-box;">
      <b><a href="${segs.join('/')}" target="_blank">${feature.properties.name}</a></b><br>
      Casos estimados: ${feature.properties.casos}<br>
      Últimas semanas:
      <br>
      <br>
      <div style="display: flex; justify-content: center;">
        <span id="${sparkId}" class="inlinesparkline"></span>
      </div>
    </div>`
  );

  layer.setStyle(style(feature, focus))

  layer.on({
    mouseover: highlightFeature,
    mouseout: resetHighlight,
    popupopen: () => renderSparkline(`#${sparkId}`, feature.properties.series)
  });
}
