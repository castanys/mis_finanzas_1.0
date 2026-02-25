-- Corrección de las 227 combinaciones inválidas restantes

-- 1. INGRESO/Inversión/Intereses → INGRESO/Intereses/(vacío)
UPDATE transacciones SET cat1='Intereses', cat2='' WHERE tipo='INGRESO' AND cat1='Inversión';

-- 2. INGRESO/Otros/Paternidad → INGRESO/Otros/(vacío)
UPDATE transacciones SET cat2='' WHERE tipo='INGRESO' AND cat1='Otros';

-- 3. INGRESO/Liquidación → INGRESO/Otros/(vacío)
UPDATE transacciones SET cat1='Otros', cat2='' WHERE tipo='INGRESO' AND cat1='Liquidación';

-- 4. INGRESO/Restauración → INGRESO/Otros/(vacío)
UPDATE transacciones SET cat1='Otros', cat2='' WHERE tipo='INGRESO' AND cat1='Restauración';

-- 5. GASTO/Wallapop → debería ser INGRESO/Wallapop, pero si son gastos (comisiones) → GASTO/Comisiones
UPDATE transacciones SET cat1='Comisiones', cat2='' WHERE tipo='GASTO' AND cat1='Wallapop';

-- 6. GASTO/Liquidación → GASTO/Finanzas/Liquidación
UPDATE transacciones SET cat1='Finanzas', cat2='Liquidación' WHERE tipo='GASTO' AND cat1='Liquidación';

-- 7. INGRESO/Inversión/Rebalanceo → INGRESO/Otros
UPDATE transacciones SET cat1='Otros', cat2='' WHERE tipo='INGRESO' AND cat1='Inversión';

-- 8. GASTO/Otros → GASTO/Compras/Otros
UPDATE transacciones SET cat1='Compras', cat2='Otros' WHERE tipo='GASTO' AND cat1='Otros';

-- 9. INGRESO/Ropa y Calzado → INGRESO/Otros
UPDATE transacciones SET cat1='Otros', cat2='' WHERE tipo='INGRESO' AND cat1='Ropa y Calzado';

-- 10. INVERSION/Fondos/Venta → ya es válido (acabamos de agregar)
-- No requiere corrección
