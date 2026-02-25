# CHANGELOG — Maestros de Categorización

Documento que registra todos los cambios realizados a los maestros CSV de validación y clasificación.

---

## Versión 8 (v8) — 2026-02-18 [ACTUAL]

**Archivo**: `Validacion_Categorias_Finsense_MASTER_v8.csv`

**Descripción**: Versión con unificación de hashes, importación de transacciones faltantes, y whitelist actualizada.

### Cambios implementados en esta versión

| Aspecto | Cambios | Transacciones afectadas | Estado |
|---------|---------|------------------------|--------|
| Migración MD5 → SHA256 | 330 hashes MD5 recalculados a SHA256 | 330 | ✅ Realizado |
| Importación Openbank faltantes | 383 transacciones nuevas importadas | +383 | ✅ Realizado |
| Eliminación duplicados | 23 duplicados reales eliminados | -23 | ✅ Realizado |
| 4 nuevas reglas merchants | ABONO EN LA TARJETA, REGULARIZACION COMPRA EN, REGULARIZACION APPLE, RETR. COMPRA RENTA | — | ✅ En merchants.py |
| Actualización whitelist | VALID_COMBINATIONS actualizada con 188 combinaciones reales | — | ✅ En valid_combos.py |
| SIN_CLASIFICAR resueltos | 20 transacciones clasificadas (0 restantes) | 20 | ✅ Aplicado |

### Totales en v8

- **Transacciones**: 15,420 (antes v6: 15,060)
- **Período**: 2004-06-23 a 2026-01-30
- **Hashes SHA256**: 15,420 (100%, antes: 15,060)
- **Hashes MD5**: 0 (antes: 330)
- **Combinaciones Cat1|Cat2 válidas**: 188
- **Combinaciones inválidas**: 0 ✅
- **SIN_CLASIFICAR**: 0 ✅

### Reglas nuevas en merchants.py

```python
# Línea 227-229
("ABONO EN LA TARJETA", "Cashback", ""),  # Reembolsos/abonos a tarjeta (sin merchant)
("REGULARIZACION COMPRA EN", "Cashback", ""),  # Regularizaciones de compra sin merchant
("REGULARIZACION APPLE", "Suscripciones", "Apple"),  # Regularización Apple pay
("RETR. COMPRA RENTA", "Inversión", "Intereses"),  # Retorno de compra de renta variable
```

### Cambios en pipeline.py

- **Línea 200-208**: Eliminación de fallback MD5. Ahora lanza excepción si falta hash, obligando a arreglar parsers.

---

## Versión 7 (v7) — 2026-02-18 [ANTERIOR]

**Archivo**: `Validacion_Categorias_Finsense_MASTER_v7.csv`

**Descripción**: Versión intermedia con importación de 383 transacciones faltantes.

### Cambios vs v6

- **Transacciones**: 15,060 → 15,420 (importadas 383 Openbank faltantes)
- **Método**: Parseadas de `input/openbank_TOTAL_ES3600730100550435513660_EUR.csv`
- **Estado**: Completamente clasificadas tras reclassify_all.py

---

## Versión 6 (v6) — 2026-02-18

**Archivo**: `Validacion_Categorias_Finsense_MASTER_v6.csv`

**Descripción**: Versión con mejoras de categorización Punto 3 (Compras/Otros).

### Cambios implementados en esta versión

| Aspecto | Cambios | Transacciones afectadas | Estado |
|---------|---------|------------------------|--------|
| 5 nuevas Cat2 | Vinos, Muebles, Videojuegos, Japonés, Entretenimiento | — | ✅ En taxonomia.py |
| 17 reglas merchant | CEDIPSA, PRIMARK, SUSHI, JYSK, IKEA, STEAM, VINOSELECCION, etc. | 147 | ✅ En merchants.py |
| Compras/Otros mejorada | 1,697 → 1,550 | 147 | ✅ Aplicado |
| Nuevas Cat2 en BD | Vinos (2), Muebles (26), Videojuegos (3), Japonés (14), Entretenimiento (9) | 54 | ✅ Aplicado |

### Totales en v6

- **Transacciones**: 15,060 (sin cambios vs v5)
- **Período**: 2004-09-08 a 2026-01-30
- **Cat2 nuevas**: 5 (en taxonomia.py)
- **Reglas nuevas**: 17 (en merchants.py)
- **Compras/Otros**: 1,550 (antes: 1,697)
- **Combinaciones válidas**: 140+ (todas en whitelist)
- **Combinaciones inválidas**: 0 ✅

---

## Versión 5 (v5) — 2026-02-18

**Archivo**: `Validacion_Categorias_Finsense_MASTER_v5.csv`

**Descripción**: Primera versión regenerada desde la BD después de las mejoras de categorización.

### Cambios implementados en esta versión

| Aspecto | Cambios | Transacciones afectadas | Estado |
|---------|---------|------------------------|--------|
| REPSOL Luz | 14 transacciones de `Recibos/Otros` → `Recibos/Luz` | 14 | ✅ Aplicado |
| Regla en merchants.py | Agregada `("RECIBO REPSOL", "Recibos", "Luz")` | — | ✅ En código |
| MyInvestor | `ABONO POR TRANSFERENCIA` → `Renta Variable/Compra` + `CARGO POR TRANSFERENCIA` → `Renta Variable/Venta` | — | ✅ En código (sesión anterior) |
| B100 Transferencias Internas | ES66 (SAVE) + ES95 (HEALTH) clasificadas como `TRANSFERENCIA/Interna` | 71 | ✅ Aplicado (sesión anterior) |
| Combinaciones inválidas | 742 combinaciones corregidas en BD | — | ✅ Aplicado (sesión anterior) |
| Taxonomía | Agregadas: `GASTO/Wallapop`, `GASTO/Liquidación`, `INVERSION/Cripto/MRCR`, `INVERSION/Cripto/Otros` | — | ✅ En código |

### Totales en v5

- **Transacciones**: 15,060
- **Período**: 2004-09-08 a 2026-01-30
- **Bancos soportados**: 7
- **Combinaciones válidas**: 130 (todas dentro de las 159 definidas en taxonomía.py)
- **Combinaciones inválidas**: 0 ✅

### Generación

```bash
# Comando usado para generar v5 desde BD
python3 << 'EOF'
import csv
import sqlite3

conn = sqlite3.connect('finsense.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        strftime('%d/%m/%Y', fecha) as fecha,
        importe, descripcion, banco, cuenta, tipo, cat1, cat2, hash, id
    FROM transacciones
    ORDER BY id
""")

rows = cursor.fetchall()

with open('validate/Validacion_Categorias_Finsense_MASTER_v5.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerow(['Fecha', 'Importe', 'Descripción', 'Banco', 'Cuenta', 'Tipo', 'Cat1', 'Cat2', 'Hash', 'id'])
    for row in rows:
        writer.writerow([row['fecha'], row['importe'], row['descripcion'], row['banco'], row['cuenta'], 
                        row['tipo'], row['cat1'], row['cat2'], row['hash'], row['id']])

conn.close()
EOF
```

---

## Versión 4 (v4) — Pre-sesión actual

**Archivo**: `Validacion_Categorias_Finsense_MASTER_v4.csv`

**Descripción**: Maestro anterior. Todavía en validación.

**Cambios respecto a v3**:
- Correcciones de combinaciones inválidas (parcial)
- Datos de B100 ES66/ES95 (parcial)

---

## Versión 3 (v3) — Línea base de esta sesión

**Archivo**: `Validacion_Categorias_Finsense_MASTER_v3.csv`

**Descripción**: Maestro usado como entrada para `reclassify_all.py` en esta sesión.

**Estado**: Validado contra transacciones reales (100% Cat1 accuracy, 100% Cat2 accuracy).

**Notas**:
- Incluye 242 transacciones con `Cat2=Devoluciones`
- Incluye 83 transacciones B100 como `TRANSFERENCIA/Interna`
- Incluye 14 REPSOL como `Recibos/Otros` (corregidas en v5)

---

## Próximos cambios previstos

### Sesión actual (en progreso)

- [ ] Punto 2: Mejorar `Recibos/Otros` (236 PayPal, 20 ONEY, 3 WIZINK, 2 VINOSELECCION, etc.)
- [ ] Punto 3: Mejorar `Compras/Otros` (1,763 tx — extraer merchant de "COMPRA EN...")
- [ ] Validar otros meses con `validate_month.py`
- [ ] Auditar `TRANSFERENCIA/Interna` y `INGRESO/Otros`

### Cómo usar este documento

1. **Al hacer cambios**: Documenta aquí la regla/palabra clave agregada y el reclassify_all.py completado.
2. **Al generar nuevo maestro**: Actualiza la sección correspondiente con transacciones afectadas.
3. **Para revertir a una versión anterior**: Usa el CSV histórico como entrada para `reclassify_all.py` con `--input-csv validate/Validacion_Categorias_Finsense_MASTER_v[N].csv`

---

## Estructura de cambios por tipo

### Cambios en `merchants.py`

Reglas agregadas en esta sesión:

```python
# Línea 106 (RECIBOS section)
("RECIBO REPSOL", "Recibos", "Luz"),  # REPSOL luz (domiciliaciones periódicas)
```

**Efecto**: La Capa 2 (Merchant Lookup) ahora captura REPSOL con palabra "RECIBO" y lo clasifica como Luz. Esto respalda el cambio en exact_match (maestro CSV).

### Cambios en maestro CSV (v3 → v5)

| Descripción | Cambio | Líneas | Método |
|-------------|--------|--------|--------|
| RECIBO REPSOL (sin GAS) | Otros → Luz | 14 líneas | Script Python + actualización v3 |

**Método**: Se ejecutó un script Python que leyó v3.csv, cambió cat2 de las 14 líneas que coincidían con `"RECIBO REPSOL" AND "GAS" NOT IN descripcion`, y escribió de vuelta.

### Cambios en `taxonomia.py`

Categorías agregadas:

```python
"GASTO": {
    ...
    "Wallapop": [],       # Nueva (Compra/venta P2P)
    "Liquidación": [],    # Nueva (Liquidación de inversiones)
    ...
},
"INVERSION": {
    "Cripto": ["Nexo", "Binance", "Bit2Me", "RAMP", "MRCR", "Otros"],  # +MRCR, +Otros
    ...
}
```

---

## Validaciones realizadas

### v5 (actual)

✅ 0 combinaciones inválidas
✅ REPSOL Luz: 14 transacciones correctas
✅ Total transacciones: 15,060

### v3 (línea base)

✅ 0 combinaciones inválidas (después de correcciones masivas)
✅ 100% Cat1 accuracy vs datos maestros
✅ 100% Cat2 accuracy vs datos maestros

---

## Notas operacionales

1. **Exact Match tiene prioridad sobre Merchants**: Si una descripción está en el maestro CSV exacta, Capa 1 gana. Por eso es crítico mantener el maestro CSV actualizado.

2. **Regenerar v5 frecuentemente**: Después de hacer `reclassify_all.py`, siempre regenerar el maestro v5 desde la BD para tener un snapshot actual.

3. **No editar CSV directamente**: Prefiere usar scripts Python + reprocesar. Es más auditable.

4. **Control de versiones**: Mantener v3, v4, v5 en el repo. Si necesitas revertir cambios, tienes el CSV histórico.

---

**Última actualización**: 2026-02-18 (Sesión 2 — BUILD, Hashes + Importación + Whitelist)
**Próxima revisión**: Sesión 3 — Auditar TRANSFERENCIA/Interna, INGRESO/Otros, Puntos 2 y 3
