/* =====================================================================
   mapa.js — Mapa Leaflet y representación de las respuestas GeoJSON
   ===================================================================== */

const mapa = L.map("mapa", { zoomControl: true }).setView([4.46, -75.68], 10);

// ---- Mapas base ----
const baseOSM = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, attribution: "© OpenStreetMap"
}).addTo(mapa);
const baseSatelite = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  { maxZoom: 19, attribution: "Esri World Imagery" });
const baseTopo = L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
  maxZoom: 17, attribution: "© OpenTopoMap (CC-BY-SA)"
});

// ---- Capas que se llenan con las respuestas de la API ----
const capaMunicipios = L.geoJSON(null, {
  style: { color: "#6d727a", weight: 1.5, fillColor: "#ffffff", fillOpacity: 0.05, dashArray: "4 3" },
  onEachFeature: (f, capa) => capa.bindTooltip(f.properties.nombre, { sticky: true })
}).addTo(mapa);

const capaVertices = L.geoJSON(null, {
  pointToLayer: (f, latlng) => L.marker(latlng, { icon: iconoVertice("#2f3237") }),
  onEachFeature: (f, capa) => capa.bindPopup(popupVertice(f.properties))
}).addTo(mapa);

const COLORES_SERVICIO = {
  "Levantamiento planimétrico": "#4f7cac",
  "Levantamiento planialtimétrico": "#2e5d8a",
  "Georreferenciación GNSS": "#b8902f",
  "Deslinde predial": "#a0522d",
  "Diseño vial": "#7b4f9e",
  "Agricultura de precisión": "#3f7d4e"
};
const capaProyectos = L.geoJSON(null, {
  style: f => estiloProyecto(f, false)
}).addTo(mapa);

const capaCercanos = L.layerGroup().addTo(mapa);   // F3: líneas proyecto → vértice
const capaAmarre = L.layerGroup().addTo(mapa);     // F5: punto clicado

L.control.layers(
  { "OpenStreetMap": baseOSM, "Satélite (Esri)": baseSatelite, "Topográfico": baseTopo },
  { "Municipios (IGAC)": capaMunicipios, "Vértices geodésicos (IGAC)": capaVertices,
    "Proyectos Line Top": capaProyectos, "Vértices cercanos (F3)": capaCercanos }
).addTo(mapa);
L.control.scale({ imperial: false }).addTo(mapa);

// Coordenadas del cursor (WGS84)
mapa.on("mousemove", e => {
  document.getElementById("coordenadas").textContent =
    `Lat ${e.latlng.lat.toFixed(6)}, Lon ${e.latlng.lng.toFixed(6)}`;
});

// ---------------------------------------------------------------------
function iconoVertice(color) {
  return L.divIcon({
    className: "",
    html: `<svg width="18" height="18" viewBox="0 0 18 18"><path d="M9 1 L17 16 L1 16 Z" fill="${color}" stroke="#fff" stroke-width="1.5"/><circle cx="9" cy="11" r="1.8" fill="#fff"/></svg>`,
    iconSize: [18, 18], iconAnchor: [9, 12]
  });
}

function estiloProyecto(f, seleccionado) {
  const color = COLORES_SERVICIO[f.properties.tipo_servicio] || "#555";
  return { color: seleccionado ? "#e0a800" : color, weight: seleccionado ? 4 : 2,
           fillColor: color, fillOpacity: seleccionado ? 0.45 : 0.3 };
}

function fmt(n, dec = 2) {
  return (n === null || n === undefined) ? "—"
    : Number(n).toLocaleString("es-CO", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function popupVertice(p) {
  return `<b>Vértice ${p.nomenclatura}</b><br>${p.nombre || ""}<table>
    <tr><td>Tipo</td><td>${p.tipo || "—"}</td></tr>
    <tr><td>Municipio</td><td>${p.municipio || "—"}</td></tr>
    <tr><td>Este (CTM12)</td><td>${fmt(p.este_ctm12, 3)} m</td></tr>
    <tr><td>Norte (CTM12)</td><td>${fmt(p.norte_ctm12, 3)} m</td></tr>
    <tr><td>h elipsoidal</td><td>${p.altura_elipsoidal != null ? fmt(p.altura_elipsoidal, 3) + " m" : "—"}</td></tr>
  </table>`;
}

/** Leyenda de tipos de servicio */
const leyendaServicios = L.control({ position: "bottomright" });
leyendaServicios.onAdd = () => {
  const div = L.DomUtil.create("div", "leyenda");
  div.innerHTML = "<h4>Proyectos por servicio</h4>" +
    Object.entries(COLORES_SERVICIO).map(([t, c]) => `<i style="background:${c}"></i>${t}`).join("<br>") +
    `<br><span style="display:inline-block;width:14px;margin-right:6px">${iconoVertice("#2f3237").options.html}</span>Vértice geodésico IGAC`;
  return div;
};
leyendaServicios.addTo(mapa);

// ---------------------------------------------------------------------
// F4: mapa temático (coropletas) con las hectáreas levantadas por municipio
// ---------------------------------------------------------------------
const RAMPA = ["#fbf6e9", "#f3e3b3", "#e6c770", "#c9a23f", "#8f6d1c"];
let leyendaTematica = null;

function claseTematica(valor, cortes) {
  if (!valor) return RAMPA[0];
  for (let i = cortes.length - 1; i >= 0; i--) if (valor >= cortes[i]) return RAMPA[i + 1];
  return RAMPA[1];
}

function aplicarTematico(estadisticas) {
  const porCodigo = Object.fromEntries(estadisticas.map(e => [e.cod_dane, e]));
  const max = Math.max(...estadisticas.map(e => Number(e.area_levantada_ha)), 0);
  const cortes = max > 0 ? [max * 0.25, max * 0.5, max * 0.75].map(v => +v.toFixed(1)) : [0, 0, 0];
  cortes.unshift(0.01);

  capaMunicipios.eachLayer(capa => {
    const e = porCodigo[capa.feature.properties.cod_dane];
    const ha = e ? Number(e.area_levantada_ha) : 0;
    capa.setStyle({ fillColor: claseTematica(ha, cortes.slice(1)), fillOpacity: 0.75, color: "#6d727a", weight: 1, dashArray: null });
    capa.setTooltipContent(`${capa.feature.properties.nombre}: ${e ? e.num_proyectos : 0} proyectos · ${fmt(ha)} ha`);
  });
  capaMunicipios.bringToBack();

  if (leyendaTematica) mapa.removeControl(leyendaTematica);
  leyendaTematica = L.control({ position: "bottomleft" });
  leyendaTematica.onAdd = () => {
    const div = L.DomUtil.create("div", "leyenda");
    div.style.marginBottom = "30px";
    div.innerHTML = "<h4>Hectáreas levantadas</h4>" +
      `<i style="background:${RAMPA[0]}"></i>Sin proyectos<br>` +
      [1, 2, 3, 4].map(i => {
        const desde = fmt(i === 1 ? 0 : cortes[i - 1], 1);
        const hasta = i < 4 ? fmt(cortes[i], 1) : fmt(max, 1);
        return `<i style="background:${RAMPA[i]}"></i>${desde} – ${hasta} ha`;
      }).join("<br>");
    return div;
  };
  leyendaTematica.addTo(mapa);
}

function quitarTematico() {
  capaMunicipios.resetStyle();
  capaMunicipios.eachLayer(c => c.setTooltipContent(c.feature.properties.nombre));
  if (leyendaTematica) { mapa.removeControl(leyendaTematica); leyendaTematica = null; }
}
