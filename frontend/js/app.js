/* =====================================================================
   app.js — Interacciones del usuario
   Cada función indica la funcionalidad (F1…F5) y el endpoint que usa.
   ===================================================================== */

const $ = id => document.getElementById(id);
let proyectoSeleccionado = null;   // id del proyecto activo (F2/F3)

// ---------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  await verificarConexion();
  await cargarCatalogos();
  await cargarCapasBase();      // F1
  await cargarProyectos();      // F1 + filtros
  conectarEventos();
});

/** GET /api/estado — muestra si hay conexión con PostgreSQL/PostGIS */
async function verificarConexion() {
  const etiqueta = $("estado-conexion");
  try {
    const e = await pedirJSON("/api/estado");
    etiqueta.className = "estado estado--ok";
    etiqueta.textContent = `● PostGIS ${e.postgis} · ${e.proyectos} proyectos · ${e.vertices_geodesicos} vértices`;
    etiqueta.title = `${e.postgresql} — BD: ${e.base_de_datos}`;
  } catch (err) {
    etiqueta.className = "estado estado--error";
    etiqueta.textContent = "● Sin conexión con la API / PostgreSQL";
    etiqueta.title = err.message;
  }
}

/** GET /api/catalogos — llena los <select> con valores que vienen de la BD */
async function cargarCatalogos() {
  try {
    const c = await pedirJSON("/api/catalogos");
    llenarSelect($("f-municipio"), (c.municipios || []).map(m => [m.cod_dane, m.nombre]));
    llenarSelect($("f-tipo"), (c.tipos_servicio || []).map(t => [t, t]));
    llenarSelect($("f-estado"), (c.estados || []).map(t => [t, t]));
    llenarSelect($("f-anio"), (c.anios || []).map(a => [a, a]));
  } catch (err) { console.error(err); }
}

function llenarSelect(select, pares) {
  pares.forEach(([valor, texto]) => select.add(new Option(texto, valor)));
}

// ---------------------------------------------------------------------
// F1. Visualización: GET /api/municipios y GET /api/vertices
// ---------------------------------------------------------------------
async function cargarCapasBase() {
  try {
    const [municipios, vertices] = await Promise.all([
      pedirJSON("/api/municipios"),
      pedirJSON("/api/vertices")
    ]);
    capaMunicipios.addData(municipios);
    capaVertices.addData(vertices);
    if (capaMunicipios.getLayers().length) mapa.fitBounds(capaMunicipios.getBounds());
  } catch (err) { alert("Error cargando capas: " + err.message); }
}

// ---------------------------------------------------------------------
// F1 + F2 (búsqueda) + F4 (filtro combinado): GET /api/proyectos?...
// ---------------------------------------------------------------------
function leerFiltros() {
  return {
    buscar: $("f-buscar").value.trim(),
    municipio: $("f-municipio").value,
    tipo: $("f-tipo").value,
    estado: $("f-estado").value,
    anio: $("f-anio").value
  };
}

async function cargarProyectos() {
  const filtros = leerFiltros();
  try {
    const geojson = await pedirJSON("/api/proyectos", filtros);
    capaProyectos.clearLayers();
    capaProyectos.addData(geojson);
    capaProyectos.eachLayer(capa => {
      const p = capa.feature.properties;
      capa.bindTooltip(`${p.codigo} · ${p.nombre}`, { sticky: true });
      capa.on("click", ev => {
        L.DomEvent.stopPropagation(ev);
        if (!$("chk-amarre").checked) seleccionarProyecto(p.id);
        else consultarPunto(ev.latlng);
      });
    });
    pintarLista(geojson.features);

    const totalHa = geojson.features.reduce((s, f) => s + Number(f.properties.area_ha), 0);
    $("resumen-filtro").textContent =
      `${geojson.features.length} proyecto(s) · ${fmt(totalHa)} ha en total`;

    if (geojson.features.length && Object.values(filtros).some(v => v)) {
      mapa.fitBounds(capaProyectos.getBounds(), { maxZoom: 15, padding: [30, 30] });
    }
    if ($("chk-tematico").checked) await cargarTematico();
  } catch (err) { alert(err.message); }
}

function pintarLista(features) {
  const ul = $("lista-proyectos");
  ul.innerHTML = "";
  features.forEach(f => {
    const p = f.properties;
    const li = document.createElement("li");
    li.dataset.id = p.id;
    li.innerHTML = `<b>${p.codigo}</b> ${p.nombre}<br><small>${p.municipio} · ${p.tipo_servicio} · ${fmt(p.area_ha)} ha</small>`;
    li.addEventListener("click", () => seleccionarProyecto(p.id, true));
    ul.appendChild(li);
  });
  if (!features.length) ul.innerHTML = "<li>Ningún proyecto cumple el filtro.</li>";
}

// ---------------------------------------------------------------------
// F2. Consulta de atributos: GET /api/proyectos/{id}
// ---------------------------------------------------------------------
async function seleccionarProyecto(id, acercar = false) {
  try {
    const p = await pedirJSON(`/api/proyectos/${id}`);
    proyectoSeleccionado = p.id;
    $("btn-cercanos").disabled = false;
    capaCercanos.clearLayers();
    $("resultado-cercanos").innerHTML = "";

    // Resaltar en el mapa y en la lista
    capaProyectos.eachLayer(c => c.setStyle(estiloProyecto(c.feature, c.feature.properties.id === p.id)));
    document.querySelectorAll("#lista-proyectos li").forEach(li =>
      li.classList.toggle("activo", Number(li.dataset.id) === p.id));
    if (acercar) {
      capaProyectos.eachLayer(c => {
        if (c.feature.properties.id === p.id) mapa.fitBounds(c.getBounds(), { maxZoom: 16, padding: [40, 40] });
      });
    }

    const equipos = p.equipos.length
      ? p.equipos.map(e => `${e.tipo} ${e.marca} ${e.modelo} (${e.codigo_inventario})`).join("<br>")
      : "—";
    $("ficha").className = "ficha";
    $("ficha").innerHTML = `
      <h3>${p.codigo} — ${p.nombre}</h3>
      <dl>
        <dt>Servicio</dt><dd>${p.tipo_servicio}</dd>
        <dt>Estado</dt><dd>${p.estado} · ${p.fecha}</dd>
        <dt>Cliente</dt><dd>${p.cliente.nombre} (${p.cliente.tipo})</dd>
        <dt>Municipio</dt><dd>${p.municipio} (${p.cod_dane})${p.dentro_del_municipio ? "" : " ⚠ cruza el límite"}</dd>
        <dt>Área CTM12</dt><dd>${fmt(p.area_ctm12_ha, 4)} ha</dd>
        <dt>Área elipsoidal</dt><dd>${fmt(p.area_elipsoidal_ha, 4)} ha</dd>
        <dt>Perímetro</dt><dd>${fmt(p.perimetro_m)} m · ${p.vertices_poligono} vértices</dd>
        <dt>Centroide E/N</dt><dd>${fmt(p.centroide_este, 3)} / ${fmt(p.centroide_norte, 3)}</dd>
        <dt>Centroide φ/λ</dt><dd>${p.centroide_lat}, ${p.centroide_lon}</dd>
        <dt>Equipos</dt><dd>${equipos}</dd>
      </dl>`;
  } catch (err) { alert(err.message); }
}

// ---------------------------------------------------------------------
// F3. Consulta espacial: GET /api/proyectos/{id}/vertices-cercanos
// ---------------------------------------------------------------------
async function buscarVerticesCercanos() {
  if (!proyectoSeleccionado) return;
  const radio = $("f-radio").value, limite = $("f-limite").value;
  try {
    const geojson = await pedirJSON(`/api/proyectos/${proyectoSeleccionado}/vertices-cercanos`,
                                    { radio_m: radio, limite: limite });
    capaCercanos.clearLayers();
    const contenedor = $("resultado-cercanos");
    if (!geojson.features.length) {
      contenedor.innerHTML = `<p class="nota">No hay vértices a menos de ${fmt(radio, 0)} m.</p>`;
      return;
    }
    // Línea más corta (ST_ShortestLine) + marcador resaltado + etiqueta con la distancia
    const grupo = L.geoJSON(geojson, {
      style: { color: "#c0392b", weight: 2.5, dashArray: "6 4" },
      onEachFeature: (f, capa) => {
        const p = f.properties;
        capa.bindTooltip(`${fmt(p.distancia_m)} m`, { permanent: true, direction: "center", className: "etiqueta-distancia" });
        L.marker([p.lat, p.lon], { icon: iconoVertice("#c0392b") })
          .bindPopup(`<b>${p.nomenclatura}</b><br>Distancia: ${fmt(p.distancia_m)} m<br>Azimut: ${fmt(p.azimut_grados, 4)}°`)
          .addTo(capaCercanos);
      }
    }).addTo(capaCercanos);
    mapa.fitBounds(grupo.getBounds(), { padding: [40, 40] });

    contenedor.innerHTML = `<table><tr><th>Vértice</th><th>Distancia (m)</th><th>Azimut</th></tr>` +
      geojson.features.map(f => `<tr><td>${f.properties.nomenclatura}</td>` +
        `<td class="num">${fmt(f.properties.distancia_m)}</td>` +
        `<td class="num">${fmt(f.properties.azimut_grados, 2)}°</td></tr>`).join("") + "</table>";
  } catch (err) { alert(err.message); }
}

// ---------------------------------------------------------------------
// F4. Mapa temático: GET /api/estadisticas/municipios?tipo=&estado=&anio=
// ---------------------------------------------------------------------
async function cargarTematico() {
  const f = leerFiltros();
  try {
    const datos = await pedirJSON("/api/estadisticas/municipios", { tipo: f.tipo, estado: f.estado, anio: f.anio });
    aplicarTematico(datos);
    const tabla = $("tabla-tematica");
    tabla.classList.remove("oculto");
    tabla.innerHTML = `<table><tr><th>Municipio</th><th>Proy.</th><th>Hectáreas</th></tr>` +
      datos.filter(d => d.num_proyectos > 0).map(d =>
        `<tr><td>${d.nombre}</td><td class="num">${d.num_proyectos}</td><td class="num">${fmt(d.area_levantada_ha)}</td></tr>`
      ).join("") + "</table>";
  } catch (err) { alert(err.message); }
}

// ---------------------------------------------------------------------
// F5. Punto de amarre: GET /api/punto?lat=&lon=
// ---------------------------------------------------------------------
async function consultarPunto(latlng) {
  try {
    const r = await pedirJSON("/api/punto", { lat: latlng.lat.toFixed(7), lon: latlng.lng.toFixed(7) });
    capaAmarre.clearLayers();
    const filas = r.vertices_cercanos.map(v =>
      `<tr><td>${v.nomenclatura}</td><td>${fmt(v.distancia_m)} m</td><td>${fmt(v.azimut_grados, 4)}°</td></tr>`).join("");
    r.vertices_cercanos.forEach(v =>
      L.polyline([latlng, [v.lat, v.lon]], { color: "#b8902f", weight: 1.5, dashArray: "3 4" }).addTo(capaAmarre));
    L.circleMarker(latlng, { radius: 6, color: "#b8902f", fillColor: "#fff", fillOpacity: 1, weight: 3 })
      .addTo(capaAmarre)
      .bindPopup(`<b>Punto consultado</b><table>
          <tr><td>Este (CTM12)</td><td>${fmt(r.este_ctm12, 3)} m</td></tr>
          <tr><td>Norte (CTM12)</td><td>${fmt(r.norte_ctm12, 3)} m</td></tr>
          <tr><td>Municipio</td><td>${r.municipio ? r.municipio.nombre : "Fuera del Quindío"}</td></tr>
          <tr><td>Proyecto</td><td>${r.proyecto ? r.proyecto.codigo : "—"}</td></tr></table>
          <b>Vértices más cercanos</b><table><tr><td>Vértice</td><td>Dist.</td><td>Azimut</td></tr>${filas}</table>`,
        { maxWidth: 320 })
      .openPopup();
  } catch (err) { alert(err.message); }
}

// ---------------------------------------------------------------------
// Eventos de la interfaz
// ---------------------------------------------------------------------
function conectarEventos() {
  $("btn-filtrar").addEventListener("click", cargarProyectos);
  $("f-buscar").addEventListener("keydown", e => { if (e.key === "Enter") cargarProyectos(); });
  $("btn-limpiar").addEventListener("click", () => {
    ["f-buscar", "f-municipio", "f-tipo", "f-estado", "f-anio"].forEach(id => $(id).value = "");
    capaCercanos.clearLayers();
    $("resultado-cercanos").innerHTML = "";
    cargarProyectos();
    if (capaMunicipios.getLayers().length) mapa.fitBounds(capaMunicipios.getBounds());
  });
  $("btn-cercanos").addEventListener("click", buscarVerticesCercanos);
  $("chk-tematico").addEventListener("change", e => {
    if (e.target.checked) cargarTematico();
    else { quitarTematico(); $("tabla-tematica").classList.add("oculto"); }
  });
  $("chk-amarre").addEventListener("change", e => {
    mapa.getContainer().style.cursor = e.target.checked ? "crosshair" : "";
    if (!e.target.checked) capaAmarre.clearLayers();
  });
  mapa.on("click", e => { if ($("chk-amarre").checked) consultarPunto(e.latlng); });
}
