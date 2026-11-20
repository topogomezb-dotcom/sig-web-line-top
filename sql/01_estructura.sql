-- =====================================================================
-- SIG Web Agro Medición Line Top — Geodatabase de proyectos topográficos
-- Script 01: estructura (extensión, sistema de referencia, tablas,
--            claves primarias, claves foráneas, restricciones e índices)
--
-- Ejecutar conectado a la base de datos sig_line_top:
--   psql -U postgres -d sig_line_top -f sql/01_estructura.sql
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- ---------------------------------------------------------------------
-- Sistema de referencia: MAGNA-SIRGAS / Origen-Nacional (CTM12)
-- EPSG:9377 — proyección cartográfica oficial de Colombia
-- (Resolución IGAC 471 de 2020, modificada por la 529 de 2020).
-- Algunas versiones de PostGIS no la traen en spatial_ref_sys;
-- si falta, se registra aquí.
-- ---------------------------------------------------------------------
INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, proj4text, srtext)
SELECT 9377, 'EPSG', 9377,
       '+proj=tmerc +lat_0=4 +lon_0=-73 +k=0.9992 +x_0=5000000 +y_0=2000000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs',
       'PROJCS["MAGNA-SIRGAS / Origen-Nacional",GEOGCS["MAGNA-SIRGAS",DATUM["Marco_Geocentrico_Nacional_de_Referencia",SPHEROID["GRS 1980",6378137,298.257222101],TOWGS84[0,0,0,0,0,0,0]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",4],PARAMETER["central_meridian",-73],PARAMETER["scale_factor",0.9992],PARAMETER["false_easting",5000000],PARAMETER["false_northing",2000000],UNIT["metre",1],AUTHORITY["EPSG","9377"]]'
WHERE NOT EXISTS (SELECT 1 FROM spatial_ref_sys WHERE srid = 9377);

-- Se borran las tablas si existen (en orden inverso a las dependencias)
DROP TABLE IF EXISTS proyecto_equipo     CASCADE;
DROP TABLE IF EXISTS proyectos           CASCADE;
DROP TABLE IF EXISTS equipos             CASCADE;
DROP TABLE IF EXISTS clientes            CASCADE;
DROP TABLE IF EXISTS vertices_geodesicos CASCADE;
DROP TABLE IF EXISTS municipios          CASCADE;

-- ---------------------------------------------------------------------
-- 1. MUNICIPIOS (polígonos) — Fuente: IGAC, Colombia en Mapas
-- ---------------------------------------------------------------------
CREATE TABLE municipios (
    cod_dane      VARCHAR(5)  PRIMARY KEY,           -- código DIVIPOLA (ej. 63001 = Armenia)
    nombre        VARCHAR(80) NOT NULL,
    departamento  VARCHAR(60) NOT NULL DEFAULT 'Quindío',
    geom          geometry(MultiPolygon, 9377) NOT NULL
);

-- ---------------------------------------------------------------------
-- 2. VÉRTICES GEODÉSICOS (puntos) — Fuente: IGAC, Red Geodésica Nacional
-- ---------------------------------------------------------------------
CREATE TABLE vertices_geodesicos (
    id                 SERIAL       PRIMARY KEY,
    nomenclatura       VARCHAR(30)  NOT NULL UNIQUE,   -- código del vértice asignado por el IGAC
    nombre             VARCHAR(120),
    tipo               VARCHAR(60),                   -- red pasiva / activa, orden, etc.
    altura_elipsoidal  NUMERIC(10,3),                 -- metros
    estado             VARCHAR(40),
    municipio_cod      VARCHAR(5)   REFERENCES municipios(cod_dane)
                                    ON UPDATE CASCADE ON DELETE SET NULL,
    geom               geometry(Point, 9377) NOT NULL
);

-- ---------------------------------------------------------------------
-- 3. CLIENTES de Agro Medición Line Top (sin datos personales sensibles)
-- ---------------------------------------------------------------------
CREATE TABLE clientes (
    id             SERIAL       PRIMARY KEY,
    nombre         VARCHAR(120) NOT NULL,
    tipo_cliente   VARCHAR(30)  NOT NULL
                   CHECK (tipo_cliente IN ('Persona natural','Empresa','Entidad pública','Asociación')),
    municipio_cod  VARCHAR(5)   REFERENCES municipios(cod_dane)
                                ON UPDATE CASCADE ON DELETE SET NULL
);

-- ---------------------------------------------------------------------
-- 4. EQUIPOS topográficos (línea de alquiler de equipos de la empresa)
-- ---------------------------------------------------------------------
CREATE TABLE equipos (
    id                    SERIAL      PRIMARY KEY,
    tipo                  VARCHAR(30) NOT NULL
                          CHECK (tipo IN ('Estación total','Receptor GNSS','Nivel','Dron','Colector')),
    marca                 VARCHAR(40) NOT NULL,
    modelo                VARCHAR(60) NOT NULL,
    codigo_inventario     VARCHAR(20) NOT NULL UNIQUE,   -- código interno de inventario de Line Top
    disponible_alquiler   BOOLEAN     NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------
-- 5. PROYECTOS topográficos (polígono del área levantada)
-- ---------------------------------------------------------------------
CREATE TABLE proyectos (
    id             SERIAL       PRIMARY KEY,
    codigo         VARCHAR(20)  NOT NULL UNIQUE,      -- ej. LT-2026-001
    nombre         VARCHAR(150) NOT NULL,
    tipo_servicio  VARCHAR(40)  NOT NULL
                   CHECK (tipo_servicio IN ('Levantamiento planimétrico',
                                            'Levantamiento planialtimétrico',
                                            'Georreferenciación GNSS',
                                            'Deslinde predial',
                                            'Diseño vial',
                                            'Agricultura de precisión')),
    fecha          DATE         NOT NULL,
    estado         VARCHAR(20)  NOT NULL DEFAULT 'Terminado'
                   CHECK (estado IN ('Cotizado','En ejecución','Terminado')),
    cliente_id     INTEGER      NOT NULL REFERENCES clientes(id)
                                ON UPDATE CASCADE ON DELETE RESTRICT,
    municipio_cod  VARCHAR(5)   NOT NULL REFERENCES municipios(cod_dane)
                                ON UPDATE CASCADE ON DELETE RESTRICT,
    geom           geometry(Polygon, 9377) NOT NULL,
    CONSTRAINT proyectos_geom_valida CHECK (ST_IsValid(geom))
);

-- ---------------------------------------------------------------------
-- 6. PROYECTO_EQUIPO — relación muchos a muchos (equipos usados en cada proyecto)
-- ---------------------------------------------------------------------
CREATE TABLE proyecto_equipo (
    proyecto_id  INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    equipo_id    INTEGER NOT NULL REFERENCES equipos(id)   ON DELETE RESTRICT,
    PRIMARY KEY (proyecto_id, equipo_id)
);

-- ---------------------------------------------------------------------
-- Índices espaciales (GiST) e índices de claves foráneas
-- ---------------------------------------------------------------------
CREATE INDEX idx_municipios_geom  ON municipios          USING GIST (geom);
CREATE INDEX idx_vertices_geom    ON vertices_geodesicos USING GIST (geom);
CREATE INDEX idx_proyectos_geom   ON proyectos           USING GIST (geom);
CREATE INDEX idx_proyectos_cliente   ON proyectos (cliente_id);
CREATE INDEX idx_proyectos_municipio ON proyectos (municipio_cod);
CREATE INDEX idx_vertices_municipio  ON vertices_geodesicos (municipio_cod);
