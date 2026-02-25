-- TAREA 2: Migración de datos históricos a Taxonomía v2
-- Ejecutar en ORDEN

-- ============================================================================
-- 2A. FUSIONES DE CAT2 (renombrar)
-- ============================================================================

-- Cafeterías → Cafetería
UPDATE transacciones SET cat2='Cafetería' WHERE cat2='Cafeterías';

-- Bares → Bar
UPDATE transacciones SET cat2='Bar' WHERE cat2='Bares';

-- Amazaon → Amazon
UPDATE transacciones SET cat2='Amazon' WHERE cat2='Amazaon';

-- AliExpress → Aliexpress
UPDATE transacciones SET cat2='Aliexpress' WHERE cat2='AliExpress';

-- Lotería → Loterías
UPDATE transacciones SET cat2='Loterías' WHERE cat2='Lotería';

-- Bazar chino → Bazar
UPDATE transacciones SET cat2='Bazar' WHERE cat2='Bazar chino';

-- Taxi/VTC → Taxi
UPDATE transacciones SET cat2='Taxi' WHERE cat2='Taxi/VTC';

-- Taller/Automoción → Taller
UPDATE transacciones SET cat2='Taller' WHERE cat2='Taller/Automoción';

-- ITV → Taller
UPDATE transacciones SET cat2='Taller' WHERE cat1='Transporte' AND cat2='ITV';

-- Aparcamiento/Peajes → Peajes
UPDATE transacciones SET cat2='Peajes' WHERE cat2='Aparcamiento/Peajes';

-- Metro/Tranvía, Autobús, Tren → Transporte público
UPDATE transacciones SET cat2='Transporte público' WHERE cat2 IN ('Metro/Tranvía', 'Autobús', 'Tren');

-- Autoescuela → Otros (Transporte)
UPDATE transacciones SET cat2='Otros' WHERE cat1='Transporte' AND cat2='Autoescuela';

-- Bizum > 0 → Bizum > (vacío)
UPDATE transacciones SET cat2='' WHERE cat1='Bizum' AND cat2='0';

-- Gasto (minúscula) → GASTO
UPDATE transacciones SET tipo='GASTO' WHERE tipo='Gasto';

-- Software fusión
UPDATE transacciones SET cat2='Software' WHERE cat2 IN ('Software/Desarrollo', 'Software/IA', 'IA', 'Cloud/Backup');

-- Cocina/Recetas → Otros (Suscripciones)
UPDATE transacciones SET cat2='Otros' WHERE cat1='Suscripciones' AND cat2='Cocina/Recetas';

-- Clínica dental → Dental
UPDATE transacciones SET cat2='Dental' WHERE cat2='Clínica dental';

-- Clínica capilar, Spa, Láser, Nutrición, CM Virgen... → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Salud y Belleza' AND cat2 IN ('Clínica capilar', 'Spa', 'Láser', 'Nutrición', 'CM Virgen de la Caridad');

-- FARMACIA CRESPO GALVEZ, MARIA DOLORES... → Farmacia
UPDATE transacciones SET cat2='Farmacia' WHERE cat2 IN ('FARMACIA CRESPO GALVEZ', 'MARIA DOLORES CRESPO GAL');

-- Ingreso cajero, Retirada cajero (GASTO) → Retirada
UPDATE transacciones SET cat2='Retirada' WHERE tipo='GASTO' AND cat1='Efectivo' AND cat2='Retirada cajero';

-- Compra Postigos → Otros (Vivienda)
UPDATE transacciones SET cat2='Otros' WHERE cat1='Vivienda' AND cat2='Compra Postigos';

-- ============================================================================
-- 2B. SEGUROS UNIFICADO
-- ============================================================================

-- Recibos > Seguro Casa → Seguros > Casa
UPDATE transacciones SET cat1='Seguros', cat2='Casa' WHERE cat1='Recibos' AND cat2='Seguro Casa';

-- Seguros > (vacío) → Seguros > Otros (si no se puede determinar)
UPDATE transacciones SET cat2='Otros' WHERE cat1='Seguros' AND cat2='';

-- ============================================================================
-- 2C. DEVOLUCIONES: INGRESO → GASTO
-- ============================================================================

-- Paso 1: Comisiones → GASTO > Comisiones > (vacío)
UPDATE transacciones SET tipo='GASTO', cat1='Comisiones', cat2='' WHERE tipo='INGRESO' AND cat1='Devoluciones' AND cat2='Comisiones';

-- Paso 2: IRPF/Hacienda → GASTO > Impuestos > IRPF
UPDATE transacciones SET tipo='GASTO', cat1='Impuestos', cat2='IRPF' WHERE tipo='INGRESO' AND cat1='Devoluciones' AND cat2 IN ('IRPF', 'Hacienda');

-- Paso 3: Regularización → GASTO > Devoluciones > (vacío)
UPDATE transacciones SET tipo='GASTO', cat1='Devoluciones', cat2='' WHERE tipo='INGRESO' AND cat1='Devoluciones' AND cat2='Regularización';

-- Paso 4: Sin Cat2 → GASTO > Devoluciones > (vacío)
UPDATE transacciones SET tipo='GASTO', cat1='Devoluciones', cat2='' WHERE tipo='INGRESO' AND cat1='Devoluciones' AND cat2='';

-- ============================================================================
-- 2D. EFECTIVO UNIFICADO
-- ============================================================================

-- INGRESO > Efectivo → GASTO > Efectivo > Ingreso
UPDATE transacciones SET tipo='GASTO', cat2='Ingreso' WHERE tipo='INGRESO' AND cat1='Efectivo';

-- Ingreso cajero → Ingreso
UPDATE transacciones SET cat2='Ingreso' WHERE tipo='GASTO' AND cat1='Efectivo' AND cat2='Ingreso cajero';

-- Retirada cajero / Retirada / (vacío) → Retirada
UPDATE transacciones SET cat2='Retirada' WHERE tipo='GASTO' AND cat1='Efectivo' AND cat2 IN ('Retirada cajero', 'Retirada', '');

-- ============================================================================
-- 2E. MERCHANTS EN RESTAURACIÓN → GENÉRICO
-- ============================================================================

-- Bares
UPDATE transacciones SET cat2='Bar' WHERE cat1='Restauración' AND cat2 IN ('A LA BARRA GASTROBAR', 'A LA BARRA', 'BAR LA PAZ', 'Bar El Gato 3', 'Beer Shooter Cartagena', 'Mastia Craft Beer', 'La Uva Jumillana', 'American Rock Bar', 'Pub', 'Cervecería', 'Taberna');

-- Restaurantes
UPDATE transacciones SET cat2='Restaurante' WHERE cat1='Restauración' AND cat2 IN ('AVALON CARTAGENA', 'RESTAURANTE INFERNUM', 'Restaurante Infernum', 'Restaurante Los Curros', 'El Pincho de Castilla', 'El Purgatorio', 'El Loco Ángel', 'El Charru', 'Colmao The Market', 'Chamfer', 'Casa Nene', 'Alpujarras', 'La Posada de la Puebla', 'Pulpería Luis', 'Scabetti', 'Biferia', 'A Vioteca do Mercado', 'Balneario San Antonio', 'WeLikeCoffee', 'Asador', 'Mesón', 'Tapería', 'Bodega', 'La Milla', 'Sushi');

-- Cafeterías
UPDATE transacciones SET cat2='Cafetería' WHERE cat1='Restauración' AND cat2 IN ('CAFETERIA PROA', 'Churrería', 'Pastelería', 'Kiosco Miguel');

-- Fast food
UPDATE transacciones SET cat2='Fast food' WHERE cat1='Restauración' AND cat2 IN ('Takos', 'Kebab', 'Hamburguesería', 'SUPERMERCADO UPPER 948');

-- Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Restauración' AND cat2 IN ('GATE GROUP INFLIGHT', 'EAT Aeropuerto Alicante', 'Santa Ana');

-- Pizzería → Restaurante
UPDATE transacciones SET cat2='Restaurante' WHERE cat1='Restauración' AND cat2='Pizzería';

-- ============================================================================
-- 2F. ALIMENTACIÓN: MERCHANTS <15 TX → OTROS
-- ============================================================================

UPDATE transacciones SET cat2='Otros' WHERE cat1='Alimentación' AND cat2 IN ('Pescadería', 'Hipermercado', 'Dia', 'Aldi', 'Alcampo', 'Consum', 'Café', 'GM Cash', 'Jamones', 'TRANSGOURMET IBERICA', 'Regularización', 'Supermercado');

-- ============================================================================
-- 2G. OTRAS LIMPIEZAS
-- ============================================================================

-- Préstamos como Cat1 independiente → Finanzas > Préstamos
UPDATE transacciones SET cat1='Finanzas', cat2='Préstamos' WHERE cat1='Préstamos' AND cat2 != 'Préstamo hermano';

-- Combustible como Cat1 → Transporte > Combustible
UPDATE transacciones SET cat1='Transporte', cat2='Combustible' WHERE cat1='Combustible';

-- Ropa y Calzado: merchants <15 → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Ropa y Calzado' AND cat2 IN ('Springfield', 'El Ganso', 'Cortefiel');

-- Ocio y Cultura: merchants → genérico
UPDATE transacciones SET cat2='Otros' WHERE cat1='Ocio y Cultura' AND cat2 IN ('Santa Ana', 'Deportes', 'Turismo', 'Cultura', 'Museos');

-- Finanzas > Paternidad (INGRESO, 4 tx) → INGRESO > Otros
UPDATE transacciones SET cat1='Otros' WHERE tipo='INGRESO' AND cat1='Finanzas';

-- Seguros > Indemnización (INGRESO, 1 tx) → INGRESO > Otros
UPDATE transacciones SET cat1='Otros' WHERE tipo='INGRESO' AND cat1='Seguros';

-- Intereses > Trade Republic → Intereses > (vacío)
UPDATE transacciones SET cat2='' WHERE tipo='INGRESO' AND cat1='Intereses' AND cat2='Trade Republic';
