/* =====================================================================
   api.js — Comunicación HTTP con la API FastAPI
   Toda petición del visor pasa por pedirJSON(), que además deja un
   registro visible (método, URL, código HTTP, tiempo y nº de elementos)
   como evidencia de la comunicación frontend ↔ API.
   ===================================================================== */

// Si el visor lo sirve la propia API (http://127.0.0.1:8000/) se usan rutas relativas;
// si se abre con Live Server u otro puerto, se apunta a la API en el puerto 8000.
const API_BASE = (location.port === "8000") ? "" : "http://127.0.0.1:8000";

/**
 * Hace una petición GET a la API y devuelve el JSON.
 * @param {string} ruta    ej. "/api/proyectos"
 * @param {object} params  parámetros de consulta; los vacíos no se envían
 */
async function pedirJSON(ruta, params = {}) {
  const url = new URL(API_BASE + ruta, location.href);
  Object.entries(params).forEach(([clave, valor]) => {
    if (valor !== "" && valor !== null && valor !== undefined) url.searchParams.set(clave, valor);
  });

  const inicio = performance.now();
  let respuesta;
  try {
    respuesta = await fetch(url);
  } catch (e) {
    registrarPeticion(url, "SIN CONEXIÓN", 0, null, false);
    throw new Error("No se pudo conectar con la API en " + (API_BASE || location.origin));
  }
  const datos = await respuesta.json();
  const ms = Math.round(performance.now() - inicio);

  let cantidad = null;
  if (datos && datos.type === "FeatureCollection") cantidad = datos.features.length + " features";
  else if (Array.isArray(datos)) cantidad = datos.length + " filas";

  registrarPeticion(url, respuesta.status, ms, cantidad, respuesta.ok);
  console.log(`[API] GET ${url.pathname}${url.search} → ${respuesta.status}`, datos);

  if (!respuesta.ok) {
    const detalle = typeof datos.detail === "string" ? datos.detail : JSON.stringify(datos.detail);
    throw new Error(`HTTP ${respuesta.status}: ${detalle}`);
  }
  return datos;
}

/** Agrega una línea al panel "Registro de peticiones HTTP". */
function registrarPeticion(url, estado, ms, cantidad, ok) {
  const lista = document.getElementById("registro-http");
  const li = document.createElement("li");
  const hora = new Date().toLocaleTimeString("es-CO");
  li.innerHTML = `${hora} GET ${decodeURIComponent(url.pathname + url.search)} → ` +
                 `<span class="${ok ? "ok" : "error"}">${estado}</span> · ${ms} ms` +
                 (cantidad ? ` · ${cantidad}` : "");
  lista.prepend(li);
}
