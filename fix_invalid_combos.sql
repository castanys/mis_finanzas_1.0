-- Corrección de combinaciones inválidas detectadas

-- ============================================================================
-- PRINCIPALES CORRECCIONES
-- ============================================================================

-- 1. GASTO/Recibos/PayPal (236 tx) → GASTO/Recibos/Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Recibos' AND cat2='PayPal';

-- 2. GASTO/Alimentación/Alimentación (231 tx) → GASTO/Alimentación/Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Alimentación' AND cat2='Alimentación';

-- 3. GASTO/Compras/Ajustes (211 tx) → GASTO/Compras/Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Compras' AND cat2='Ajustes';

-- 4. INVERSION/Comisiones/(vacío) (199 tx) → está bien (vacío es válido en INVERSION/Comisiones)
-- No requiere corrección

-- 5. INGRESO/Compras/Regularización (151 tx) → GASTO/Devoluciones/(vacío)
UPDATE transacciones SET tipo='GASTO', cat1='Devoluciones', cat2='' WHERE tipo='INGRESO' AND cat1='Compras';

-- 6. TRANSFERENCIA/Cuenta Común/Entrante (101 tx) → TRANSFERENCIA/Cuenta Común/(vacío)
UPDATE transacciones SET cat2='' WHERE cat1='Cuenta Común' AND cat2='Entrante';

-- 7. GASTO/Ropa y Calzado/Ropa y Calzado (63 tx) → GASTO/Ropa y Calzado/Ropa y Accesorios
UPDATE transacciones SET cat2='Ropa y Accesorios' WHERE cat1='Ropa y Calzado' AND cat2='Ropa y Calzado';

-- 8. GASTO/Recibos/Grandes Almacenes (43 tx) → GASTO/Recibos/Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Recibos' AND cat2='Grandes Almacenes';

-- 9. GASTO/Compras/Electrónica (42 tx) → GASTO/Compras/Tecnología
UPDATE transacciones SET cat2='Tecnología' WHERE cat1='Compras' AND cat2='Electrónica';

-- 10. GASTO/Compras/Casa (32 tx) → GASTO/Compras/Hogar
UPDATE transacciones SET cat2='Hogar' WHERE cat1='Compras' AND cat2='Casa';

-- 11. GASTO/Viajes/Aeropuerto/Duty Free → GASTO/Viajes/Aeropuerto
UPDATE transacciones SET cat2='Aeropuerto' WHERE cat1='Viajes' AND cat2 LIKE '%Aeropuerto%';

-- 12. GASTO/Restauración/A la Barra → GASTO/Restauración/Bar
UPDATE transacciones SET cat2='Bar' WHERE cat1='Restauración' AND cat2='A la Barra';

-- 13. GASTO/Compras/Panadería → GASTO/Alimentación/Panadería
UPDATE transacciones SET cat1='Alimentación', cat2='Panadería' WHERE cat1='Compras' AND cat2='Panadería';

-- 14. GASTO/Compras/Alojamiento → GASTO/Viajes/Alojamiento
UPDATE transacciones SET cat1='Viajes', cat2='Alojamiento' WHERE cat1='Compras' AND cat2='Alojamiento';

-- 15. GASTO/Recibos/Oney Servicios Financieros → GASTO/Finanzas/Préstamos
UPDATE transacciones SET cat1='Finanzas', cat2='Préstamos' WHERE cat1='Recibos' AND cat2 LIKE '%Oney%';

-- 16. GASTO/Compras/Gvb Spinnerij → GASTO/Transporte/Transporte público
UPDATE transacciones SET cat1='Transporte', cat2='Transporte público' WHERE cat1='Compras' AND cat2='Gvb Spinnerij';

-- 17. GASTO/Restauración/Avalon Cartagena → GASTO/Restauración/Restaurante
UPDATE transacciones SET cat2='Restaurante' WHERE cat1='Restauración' AND cat2='Avalon Cartagena';

-- 18. GASTO/Restauración/Kiosco → GASTO/Restauración/Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Restauración' AND cat2='Kiosco';

-- 19. GASTO/Compras/Bodega → GASTO/Alimentación/Bodega
UPDATE transacciones SET cat1='Alimentación', cat2='Bodega' WHERE cat1='Compras' AND cat2='Bodega';

-- 20. GASTO/Compras/Vino → GASTO/Alimentación/Bodega
UPDATE transacciones SET cat1='Alimentación', cat2='Bodega' WHERE cat1='Compras' AND cat2='Vino';

-- ============================================================================
-- CORRECCIONES ADICIONALES (todas las categorías inválidas restantes)
-- ============================================================================

-- Todos los Cat2 no reconocidos en Restauración → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Restauración' AND cat2 NOT IN ('Restaurante', 'Bar', 'Cafetería', 'Fast food', 'Heladería', 'Otros');

-- Todos los Cat2 no reconocidos en Compras → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Compras' AND cat2 NOT IN ('Amazon', 'El Corte Inglés', 'Leroy Merlin', 'Decathlon', 'Aliexpress', 'Online', 'Tecnología', 'Hogar', 'Estancos', 'Loterías', 'Bazar', 'Deportes', 'Ropa y Calzado', 'Otros');

-- Todos los Cat2 no reconocidos en Alimentación → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Alimentación' AND cat2 NOT IN ('Mercadona', 'Lidl', 'Carnicería', 'Carrefour', 'Cash & Carry', 'Frutería', 'Eroski', 'Bodega', 'Higinio', 'Mercado', 'Panadería', 'Otros');

-- Todos los Cat2 no reconocidos en Recibos → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Recibos' AND cat2 NOT IN ('Telefonía e Internet', 'Luz', 'Agua', 'Gas', 'Gimnasio', 'Alarma', 'Asesoría', 'Donaciones', 'Fotovoltaica', 'Otros');

-- Todos los Cat2 no reconocidos en Viajes → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Viajes' AND cat2 NOT IN ('Alojamiento', 'Vuelos', 'Transporte', 'Actividades', 'Aeropuerto', 'Otros');

-- Todos los Cat2 no reconocidos en Salud y Belleza → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Salud y Belleza' AND cat2 NOT IN ('Farmacia', 'Médico', 'Dental', 'Óptica', 'Peluquería', 'Fisioterapia', 'Perfumería', 'Otros');

-- Todos los Cat2 no reconocidos en Suscripciones → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Suscripciones' AND cat2 NOT IN ('Streaming', 'Música', 'Audible', 'Software', 'Apple', 'Waylet', 'Otros');

-- Todos los Cat2 no reconocidos en Transporte → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Transporte' AND cat2 NOT IN ('Combustible', 'Peajes', 'Parking', 'Transporte público', 'Taxi', 'Taller', 'Otros');

-- Todos los Cat2 no reconocidos en Ropa y Calzado → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Ropa y Calzado' AND cat2 NOT IN ('Carrefour Zaraiche', 'Ropa y Accesorios', 'Otros');

-- Todos los Cat2 no reconocidos en Ocio y Cultura → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Ocio y Cultura' AND cat2 NOT IN ('Cines', 'Entradas', 'Juegos', 'Otros');

-- Todos los Cat2 no reconocidos en Finanzas → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Finanzas' AND cat2 NOT IN ('Hipoteca', 'Préstamos', 'Ahorro', 'Liquidación', 'Gestoría', 'Otros');

-- Todos los Cat2 no reconocidos en Vivienda → Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Vivienda' AND cat2 NOT IN ('Limpieza', 'Mantenimiento', 'Otros');

-- TRANSFERENCIA/Cuenta Común: limpiar cualquier Cat2 no vacío
UPDATE transacciones SET cat2='' WHERE tipo='TRANSFERENCIA' AND cat1='Cuenta Común' AND cat2 != '';
