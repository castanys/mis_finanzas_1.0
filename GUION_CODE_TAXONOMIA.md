# GUIÓN CODE: Aplicar Taxonomía Canónica v2

## CONTEXTO
Hay un documento de taxonomía canónica que define TODAS las combinaciones Tipo > Cat1 > Cat2 permitidas. Cualquier combinación fuera de esa lista es un ERROR. Este guión aplica esa taxonomía a toda la BBDD.

### CAMBIO v2.1 (Febrero 2026): Devoluciones como Cat2
- **ANTES**: `Devoluciones` era Cat1 independiente (GASTO/Devoluciones)
- **AHORA**: `Devoluciones` es Cat2 dentro de cada categoría (GASTO/Compras/Devoluciones, GASTO/Restauración/Devoluciones, etc.)
- **RAZÓN**: Cuando devuelves una compra de Amazon, el neto de "Compras" debe ser 0, no $100 gasto + $100 devolución. Las devoluciones ahora viven dentro de su categoría original.

## REGLAS
1. `cp finsense.db finsense.db.bak_antes_taxonomia` ANTES DE TODO
2. NUNCA borrar y reprocesar → SQL UPDATEs quirúrgicos
3. NUNCA inventar combinaciones nuevas
4. Si una tx no encaja en la taxonomía → Cat2="Otros" dentro de su Cat1

---

## TAREA 1: Crear validador de taxonomía

Crear un fichero `taxonomia.py` (o JSON) con TODAS las combinaciones válidas. Estructura:

```python
TAXONOMIA = {
    "GASTO": {
        "Alimentación": ["Mercadona", "Lidl", "Carnicería", "Carrefour", "Cash & Carry", "Frutería", "Eroski", "Bodega", "Higinio", "Mercado", "Panadería", "Otros", "Devoluciones"],
        "Compras": ["Amazon", "El Corte Inglés", "Leroy Merlin", "Decathlon", "Aliexpress", "Online", "Tecnología", "Hogar", "Estancos", "Loterías", "Bazar", "Deportes", "Ropa y Calzado", "Otros", "Devoluciones"],
        "Restauración": ["Restaurante", "Bar", "Cafetería", "Fast food", "Heladería", "Otros", "Devoluciones"],
        "Recibos": ["Telefonía e Internet", "Luz", "Agua", "Gas", "Gimnasio", "Alarma", "Asesoría", "Donaciones", "Fotovoltaica", "Otros", "Devoluciones"],
        "Seguros": ["Casa", "Vida", "Coche", "Otros", "Devoluciones"],
        "Transporte": ["Combustible", "Peajes", "Parking", "Transporte público", "Taxi", "Taller", "Otros", "Devoluciones"],
        "Finanzas": ["Hipoteca", "Préstamos", "Ahorro", "Liquidación", "Gestoría", "Otros", "Devoluciones"],
        "Impuestos": ["IRPF", "Autónomos", "Retenciones", "IBI", "Circulación", "Pasarela/Vado", "Seguridad Social", "AEAT"],
        "Vivienda": ["Limpieza", "Mantenimiento", "Otros", "Devoluciones"],
        "Salud y Belleza": ["Farmacia", "Médico", "Dental", "Óptica", "Peluquería", "Fisioterapia", "Perfumería", "Otros", "Devoluciones"],
        "Ropa y Calzado": ["Carrefour Zaraiche", "Ropa y Accesorios", "Otros", "Devoluciones"],
        "Ocio y Cultura": ["Cines", "Entradas", "Juegos", "Otros", "Devoluciones"],
        "Deportes": ["Pádel", "Gimnasio", "Equipo deportivo", "Club", "Devoluciones"],
        "Suscripciones": ["Streaming", "Música", "Audible", "Software", "Apple", "Waylet", "Otros", "Devoluciones"],
        "Viajes": ["Alojamiento", "Vuelos", "Transporte", "Actividades", "Aeropuerto", "Otros", "Devoluciones"],
        "Efectivo": ["Retirada", "Ingreso"],
        "Cuenta Común": [""],
        "Comisiones": [""],
        "Préstamos": ["Préstamo hermano"],
    },
    "INGRESO": {
        "Nómina": [""],
        "Cashback": [""],
        "Intereses": [""],
        "Wallapop": [""],
        "Bonificación familia numerosa": [""],
        "Servicios Consultoría": [""],
        "Efectivo": [""],
        "Otros": [""],
    },
    "INVERSION": {
        "Renta Variable": ["Compra", "Venta"],
        "Cripto": ["Nexo", "Binance", "MEXC", "Bit2Me", "RAMP", ""],
        "Dividendos": [""],
        "Divisas": [""],
        "Comisiones": ["Custodia", "Retenciones", ""],
        "Aportación": [""],
        "Fondos": ["Compra", "Venta", ""],
        "Liquidación": [""],
        "Depósitos": [""],
        "Cashback": [""],
        "Intereses": [""],
    },
    "TRANSFERENCIA": {
        "Interna": [""],
        "Externa": [""],
        "Bizum": [""],
        "Cuenta Común": [""],
    }
}
```

Crear función `validar_taxonomia(tipo, cat1, cat2) -> bool` que devuelve True si la combinación es válida.

---

## TAREA 2: Migración de datos históricos (SQL UPDATEs)

Ejecutar en ORDEN. Cada bloque es un UPDATE independiente.

### 2A. Fusiones de Cat2 (renombrar)

```sql
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
```

### 2B. Seguros unificado

```sql
-- Recibos > Seguro Casa → Seguros > Casa
UPDATE transacciones SET cat1='Seguros', cat2='Casa' WHERE cat1='Recibos' AND cat2='Seguro Casa';

-- Seguros > (vacío) → necesita análisis individual
-- Los 40 tx con Cat2 vacío: ¿son Casa, Vida, Coche? Revisar descripción y asignar.
-- Si no se puede determinar → Seguros > Otros
UPDATE transacciones SET cat2='Otros' WHERE cat1='Seguros' AND cat2='';
```

### 2C. Devoluciones: INGRESO → GASTO

```sql
-- Las 66 tx de INGRESO > Devoluciones deben reclasificarse.
-- Paso 1: Las que tienen Cat2=Comisiones → GASTO > Comisiones > (vacío) con importe positivo
UPDATE transacciones SET tipo='GASTO', cat1='Comisiones', cat2='' WHERE tipo='INGRESO' AND cat1='Devoluciones' AND cat2='Comisiones';

-- Paso 2: Las de IRPF/Hacienda → GASTO > Impuestos > IRPF con importe positivo (resta del gasto fiscal)
UPDATE transacciones SET tipo='GASTO', cat1='Impuestos', cat2='IRPF' WHERE tipo='INGRESO' AND cat1='Devoluciones' AND cat2 IN ('IRPF', 'Hacienda');

-- Paso 3: Las de Regularización → GASTO > Devoluciones > (vacío)
UPDATE transacciones SET tipo='GASTO', cat1='Devoluciones', cat2='' WHERE tipo='INGRESO' AND cat1='Devoluciones' AND cat2='Regularización';

-- Paso 4: Las sin Cat2 → GASTO > Devoluciones > (vacío) (no sabemos de qué categoría son)
UPDATE transacciones SET tipo='GASTO', cat1='Devoluciones', cat2='' WHERE tipo='INGRESO' AND cat1='Devoluciones' AND cat2='';
```

### 2D. Efectivo unificado

```sql
-- INGRESO > Efectivo → GASTO > Efectivo > Ingreso
UPDATE transacciones SET tipo='GASTO', cat2='Ingreso' WHERE tipo='INGRESO' AND cat1='Efectivo';

-- GASTO > Efectivo: normalizar Cat2
-- Retirada cajero → Retirada (ya hecho arriba)
-- Ingreso cajero (si hay alguno en GASTO) → Ingreso
UPDATE transacciones SET cat2='Ingreso' WHERE tipo='GASTO' AND cat1='Efectivo' AND cat2='Ingreso cajero';
UPDATE transacciones SET cat2='Retirada' WHERE tipo='GASTO' AND cat1='Efectivo' AND cat2 IN ('Retirada cajero', 'Retirada', '');
```

### 2E. Merchants como Cat2 en Restauración → genérico

```sql
-- Todos los merchants específicos de Restauración → su tipo genérico
UPDATE transacciones SET cat2='Bar' WHERE cat1='Restauración' AND cat2 IN ('A LA BARRA GASTROBAR', 'A LA BARRA', 'BAR LA PAZ', 'Bar El Gato 3', 'Beer Shooter Cartagena', 'Mastia Craft Beer', 'La Uva Jumillana', 'American Rock Bar', 'Pub', 'Cervecería', 'Taberna');

UPDATE transacciones SET cat2='Restaurante' WHERE cat1='Restauración' AND cat2 IN ('AVALON CARTAGENA', 'RESTAURANTE INFERNUM', 'Restaurante Infernum', 'Restaurante Los Curros', 'El Pincho de Castilla', 'El Purgatorio', 'El Loco Ángel', 'El Charru', 'Colmao The Market', 'Chamfer', 'Casa Nene', 'Alpujarras', 'La Posada de la Puebla', 'Pulpería Luis', 'Scabetti', 'Biferia', 'A Vioteca do Mercado', 'Balneario San Antonio', 'WeLikeCoffee', 'Asador', 'Mesón', 'Tapería', 'Bodega', 'La Milla', 'Sushi');

UPDATE transacciones SET cat2='Cafetería' WHERE cat1='Restauración' AND cat2 IN ('CAFETERIA PROA', 'Churrería', 'Pastelería', 'Kiosco Miguel');

UPDATE transacciones SET cat2='Fast food' WHERE cat1='Restauración' AND cat2 IN ('Takos', 'Kebab', 'Hamburguesería', 'SUPERMERCADO UPPER 948');

UPDATE transacciones SET cat2='Otros' WHERE cat1='Restauración' AND cat2 IN ('GATE GROUP INFLIGHT', 'EAT Aeropuerto Alicante', 'Santa Ana');
-- Nota: Santa Ana estaba en Ocio y Cultura, si aparece en Restauración mover a Otros

-- Pizzería → Restaurante
UPDATE transacciones SET cat2='Restaurante' WHERE cat1='Restauración' AND cat2='Pizzería';
```

### 2F. Alimentación: merchants <15 tx → Otros

```sql
UPDATE transacciones SET cat2='Otros' WHERE cat1='Alimentación' AND cat2 IN ('Pescadería', 'Hipermercado', 'Dia', 'Aldi', 'Alcampo', 'Consum', 'Café', 'GM Cash', 'Jamones', 'TRANSGOURMET IBERICA', 'Regularización', 'Supermercado');
```

### 2G. Otras limpiezas

```sql
-- Préstamos como Cat1 independiente → Finanzas > Préstamos
UPDATE transacciones SET cat1='Finanzas', cat2='Préstamos' WHERE cat1='Préstamos';

-- Combustible como Cat1 → Transporte > Combustible
UPDATE transacciones SET cat1='Transporte', cat2='Combustible' WHERE cat1='Combustible';

-- Servicios Consultoría (GASTO, 1 tx) → revisar y reclasificar
-- Otros (GASTO, 2 tx) → revisar y reclasificar

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
```

---

## TAREA 3: Actualizar el clasificador

Después de migrar los datos, el clasificador (engine.py, merchants, tokens, etc.) debe generar SOLO combinaciones de la taxonomía v2.

1. Cargar `taxonomia.py` en el clasificador
2. Después de clasificar cada tx, validar contra la taxonomía
3. Si la combinación no es válida → forzar Cat2="Otros" dentro de su Cat1
4. Nunca generar Cat1 que no exista en la taxonomía

---

## TAREA 4: Validación final

### 4A. Verificar 0 combinaciones inválidas

```python
# Para CADA tx en la BBDD:
#   validar_taxonomia(tipo, cat1, cat2) debe ser True
# Reportar TODAS las que fallen
```

### 4B. Contar combinaciones únicas

```sql
SELECT tipo, cat1, cat2, COUNT(*) as n 
FROM transacciones 
GROUP BY tipo, cat1, cat2 
ORDER BY tipo, cat1, cat2;
```

Comparar con la taxonomía: ¿hay alguna que no debería estar?

### 4C. Validar los 3 meses (enero 2026, enero 2025, diciembre 2025)

Ejecutar `validate_month.py` para los 3 meses. Los 10 checks deben pasar.

### 4D. Reporte resumen

- Total tx en BBDD
- Total combinaciones Tipo/Cat1/Cat2 únicas (debe ser ≤ número de combinaciones en taxonomía)
- 0 combinaciones inválidas
- Los 3 meses validados

### CRITERIO DE ÉXITO:
**0 combinaciones fuera de la taxonomía canónica v2. Sin excepciones.**
