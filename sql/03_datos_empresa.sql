-- =====================================================================
-- Script 03: datos propios de Agro Medición Line Top
--   clientes, equipos, proyectos (polígonos en CTM12, EPSG:9377) y proyecto_equipo
-- Ejecutar DESPUÉS de 01_estructura.sql y 02_datos_igac.sql
-- =====================================================================

BEGIN;

-- Clientes
INSERT INTO clientes (id, nombre, tipo_cliente, municipio_cod) VALUES
  (1, 'Finca La Cristalina', 'Persona natural', '63272'),
  (2, 'Agropecuaria El Diamante S.A.S.', 'Empresa', '63190'),
  (3, 'Asociación de Plataneros del Bajo Quindío', 'Asociación', '63401'),
  (4, 'Constructora Andina del Café S.A.S.', 'Empresa', '63001'),
  (5, 'Junta de Acción Comunal vereda El Roble', 'Asociación', '63690'),
  (6, 'Hacienda Montebello', 'Persona natural', '63548'),
  (7, 'Inversiones Quimbaya Verde S.A.S.', 'Empresa', '63594'),
  (8, 'Cooperativa Cafetera del Sur', 'Asociación', '63302');

-- Equipos (inventario de la empresa; disponible_alquiler = se puede alquilar)
INSERT INTO equipos (id, tipo, marca, modelo, codigo_inventario, disponible_alquiler) VALUES
  (1, 'Estación total', 'Topcon', 'ES-105', 'LT-ET-01', TRUE),
  (2, 'Estación total', 'Leica', 'TS07 5"', 'LT-ET-02', TRUE),
  (3, 'Receptor GNSS', 'South', 'Galaxy G1 (base + rover)', 'LT-GN-01', TRUE),
  (4, 'Receptor GNSS', 'Hi-Target', 'V200', 'LT-GN-02', FALSE),
  (5, 'Nivel', 'Sokkia', 'B40A', 'LT-NV-01', TRUE),
  (6, 'Dron', 'DJI', 'Phantom 4 RTK', 'LT-DR-01', FALSE),
  (7, 'Colector', 'Carlson', 'RT4', 'LT-CO-01', TRUE);

-- Proyectos: geometría = polígono del área levantada, coordenadas Este/Norte en metros (CTM12)
INSERT INTO proyectos (id, codigo, nombre, tipo_servicio, fecha, estado, cliente_id, municipio_cod, geom) VALUES
  (1, 'LT-2024-001', 'Levantamiento planialtimétrico Finca La Cristalina', 'Levantamiento planialtimétrico', '2024-03-12', 'Terminado', 1, '63272',
   ST_GeomFromText('POLYGON((4704341.524 2075923.572,4704311.164 2075517.347,4704598.829 2075559.179,4704655.644 2075628.9980000001,4704681.561 2075623.317,4704341.524 2075923.572))', 9377)),
  (2, 'LT-2024-002', 'Georreferenciación predio El Diamante', 'Georreferenciación GNSS', '2024-05-20', 'Terminado', 2, '63190',
   ST_GeomFromText('POLYGON((4706176.141 2069678.462,4706096.205 2069719.0690000001,4706002.501 2069634.462,4706009.085 2069558.2550000001,4705991.921 2069522.156,4706088.955 2069480.433,4706135.492000001 2069496.0150000001,4706140.665 2069488.011,4706176.141 2069678.462))', 9377)),
  (3, 'LT-2024-003', 'Deslinde lote Villa Laura', 'Deslinde predial', '2024-07-08', 'Terminado', 4, '63470',
   ST_GeomFromText('POLYGON((4696176.015 2063536.605,4696155.489 2063564.949,4696064.201 2063568.823,4695972.025 2063452.61,4696069.074 2063386.887,4696176.015 2063536.605))', 9377)),
  (4, 'LT-2024-004', 'Lotes de plátano — mapeo de vigor con dron', 'Agricultura de precisión', '2024-09-16', 'Terminado', 3, '63401',
   ST_GeomFromText('POLYGON((4689775.67 2052169.9370000002,4689287.667 2052184.114,4689337.475000001 2052100.368,4689285.808 2051983.482,4689218.932 2051967.33,4689317.629 2051834.845,4689327.605 2051810.256,4689561.593 2051755.558,4689775.67 2052169.9370000002))', 9377)),
  (5, 'LT-2024-005', 'Diseño vía terciaria vereda El Roble', 'Diseño vial', '2024-11-04', 'Terminado', 5, '63690',
   ST_GeomFromText('POLYGON((4714472.636 2071794.411,4714474.576 2071795.036,4715640.651000001 2072012.0080000001,4715643.578 2071996.278,4714478.513 2071779.494,4713312.14 2071231.159,4713305.332 2071245.638,4714472.636 2071794.411))', 9377)),
  (6, 'LT-2025-001', 'Levantamiento lote urbano barrio La Castellana', 'Levantamiento planimétrico', '2025-02-10', 'Terminado', 4, '63001',
   ST_GeomFromText('POLYGON((4701415.155 2060743.1330000001,4701458.4860000005 2060696.7210000001,4701470.847 2060663.899,4701498.601 2060663.561,4701516.477 2060695.087,4701572.850000001 2060733.725,4701415.155 2060743.1330000001))', 9377)),
  (7, 'LT-2025-002', 'Cafetal Hacienda Montebello — agricultura de precisión', 'Agricultura de precisión', '2025-03-25', 'Terminado', 6, '63548',
   ST_GeomFromText('POLYGON((4699312.055 2038272.455,4699170.483 2038206.753,4699173.049 2038062.622,4699232.538 2038000.75,4699272.931 2037933.834,4699426.854 2038075.517,4699439.473 2038088.182,4699492.297 2038102.946,4699312.055 2038272.455))', 9377)),
  (8, 'LT-2025-003', 'Levantamiento planialtimétrico parcelación Calarcá', 'Levantamiento planialtimétrico', '2025-05-05', 'Terminado', 4, '63130',
   ST_GeomFromText('POLYGON((4708857.5540000005 2057545.963,4708731.973 2057534.599,4708721.189 2057449.843,4708703.884000001 2057431.176,4708774.413 2057312.0320000001,4708833.593 2057283.78,4708859.278 2057311.772,4708944.2 2057366.2040000001,4708857.5540000005 2057545.963))', 9377)),
  (9, 'LT-2025-004', 'Georreferenciación predio La Esperanza', 'Georreferenciación GNSS', '2025-06-18', 'Terminado', 8, '63212',
   ST_GeomFromText('POLYGON((4701665.46 2044228.174,4701545.268 2044278.624,4701427.214 2044220.8730000001,4701440.933 2044196.875,4701618.974 2044083.186,4701645.831 2044160.9370000002,4701645.332 2044162.239,4701665.46 2044228.174))', 9377)),
  (10, 'LT-2025-005', 'Deslinde finca Los Naranjos', 'Deslinde predial', '2025-08-11', 'Terminado', 7, '63594',
   ST_GeomFromText('POLYGON((4692946.265 2068602.016,4692936.879 2068712.3390000002,4692828.0600000005 2068737.242,4692608.956 2068504.315,4692589.695 2068406.391,4692946.265 2068602.016))', 9377)),
  (11, 'LT-2025-006', 'Diseño acceso vehicular mirador Buenavista', 'Diseño vial', '2025-09-22', 'Terminado', 8, '63111',
   ST_GeomFromText('POLYGON((4696041.359 2040488.716,4695321.887 2040767.404,4695327.666 2040782.324,4696048.398 2040503.148,4696049.599 2040502.563,4696050.686 2040501.786,4696770.216 2039890.767,4696759.859 2039878.571,4696041.359 2040488.716))', 9377)),
  (12, 'LT-2025-007', 'Cafetales cooperativa — inventario de lotes', 'Agricultura de precisión', '2025-11-03', 'Terminado', 8, '63302',
   ST_GeomFromText('POLYGON((4691069.244 2024452.985,4690891.019 2024476.144,4690765.681 2024337.6130000001,4690710.984 2024242.855,4690759.2700000005 2024184.969,4690857.277 2024116.432,4690864.62 2024125.523,4691093.3610000005 2024241.548,4691069.244 2024452.985))', 9377)),
  (13, 'LT-2026-001', 'Levantamiento planialtimétrico lote Portal del Edén', 'Levantamiento planialtimétrico', '2026-02-09', 'En ejecución', 4, '63001',
   ST_GeomFromText('POLYGON((4700057.546 2056967.923,4699839.994 2057003.926,4699868.905 2056964.7750000001,4699868.354 2056819.8660000002,4699997.228 2056802.349,4700042.515 2056879.624,4700057.546 2056967.923))', 9377)),
  (14, 'LT-2026-002', 'Georreferenciación predio El Recreo', 'Georreferenciación GNSS', '2026-04-14', 'Terminado', 2, '63470',
   ST_GeomFromText('POLYGON((4693355.024 2062021.608,4693143.889 2061943.8090000001,4693151.473 2061913.858,4693186.7870000005 2061842.2110000001,4693176.465 2061803.136,4693355.024 2062021.608))', 9377)),
  (15, 'LT-2026-003', 'Levantamiento planimétrico lote La Pradera', 'Levantamiento planimétrico', '2026-06-01', 'Cotizado', 1, '63190',
   ST_GeomFromText('POLYGON((4707733.777 2068463.617,4707740.976 2068476.152,4707665.288 2068517.862,4707547.78 2068347.331,4707564.997 2068362.036,4707544.767 2068334.011,4707714.051 2068341.594,4707709.398 2068400.398,4707733.777 2068463.617))', 9377)),
  (16, 'LT-2026-004', 'Plataneras Quimbaya Verde — mapeo de vigor', 'Agricultura de precisión', '2026-07-20', 'En ejecución', 7, '63594',
   ST_GeomFromText('POLYGON((4694826.314 2071515.404,4694276.82 2071771.435,4694133.821 2071770.882,4694078.67 2071611.637,4694027.159 2071559.6060000001,4694039.116 2071515.083,4694826.314 2071515.404))', 9377)),
  (17, 'LT-2026-005', 'Deslinde predio comunal El Roble', 'Deslinde predial', '2026-09-07', 'Terminado', 5, '63690',
   ST_GeomFromText('POLYGON((4714619.088 2069580.914,4714575.133 2069682.183,4714591.526000001 2069695.3020000001,4714467.517 2069812.642,4714376.856 2069817.5760000001,4714243.365 2069637.389,4714249.350000001 2069550.371,4714171.049 2069534.438,4714619.088 2069580.914))', 9377)),
  (18, 'LT-2026-006', 'Levantamiento planialtimétrico Finca La Cristalina (ampliación)', 'Levantamiento planialtimétrico', '2026-10-19', 'En ejecución', 1, '63272',
   ST_GeomFromText('POLYGON((4707411.83 2074276.522,4707122.332 2074134.281,4707129.807 2074117.367,4707109.188 2074101.986,4707147.699 2074111.395,4707136.863 2074101.592,4707237.8 2073953.59,4707411.83 2074276.522))', 9377));

-- Equipos utilizados en cada proyecto (relación muchos a muchos)
INSERT INTO proyecto_equipo (proyecto_id, equipo_id) VALUES
  (1, 2), (1, 3), (1, 5), (2, 3), (3, 1), (3, 3), (3, 7), (4, 6), (4, 4), (5, 2), (5, 5), (5, 6), (6, 1), (6, 7), (7, 6), (7, 4), (8, 2), (8, 3), (8, 5), (9, 3), (10, 1), (10, 3), (10, 7), (11, 2), (11, 5), (11, 6), (12, 6), (12, 4), (13, 2), (13, 3), (13, 5), (14, 3), (15, 1), (15, 7), (16, 6), (16, 4), (17, 1), (17, 3), (17, 7), (18, 2), (18, 3), (18, 5);

-- Se ajustan las secuencias SERIAL después de insertar con id explícito
SELECT setval('clientes_id_seq',  (SELECT MAX(id) FROM clientes));
SELECT setval('equipos_id_seq',   (SELECT MAX(id) FROM equipos));
SELECT setval('proyectos_id_seq', (SELECT MAX(id) FROM proyectos));

COMMIT;
