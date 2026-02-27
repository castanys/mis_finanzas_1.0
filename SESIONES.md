# SESIONES.md — mis_finanzas_1.0

**Propósito**: Últimas 3 sesiones completadas (detalle operativo).

**Última actualización**: 2026-02-27 — Sesión 67 COMPLETADA

**Nota**: Estado mínimo, decisiones y pendientes → leer `ESTADO.md`

---

## 🟢 Últimas 3 Sesiones

### S67 — 2026-02-27 — MÓDULO VALIDATOR: 18 CHECKS DE INTEGRIDAD ✅

**Objetivo**: Crear módulo `validator.py` que se lanza automáticamente tras cualquier carga/clasificación y detecta errores reales en datos y clasificación.

**Checks implementados (V01–V18)**:
- V01: Cat1 fuera de whitelist | V02: Combos Cat1|Cat2 inválidos | V03: tipo inconsistente con cat1/importe
- V04: Hashes duplicados | V05: Duplicados sospechosos (misma fecha+importe+desc similar) | V06: SIN_CLASIFICAR
- V07: merchant_name faltante | V08: Signo incorrecto GASTO/INGRESO | V09: Fechas inválidas
- V10: Merchants sin cat1 | V11: Banco desconocido | V12: cat2 no vacío donde debería serlo
- V13: Descripción vacía | V14: Hash NULL | V15: Importe cero
- V16: Nóminas anómalas (solo últimos 5 años) | V17: Outliers estadísticos por cat1 (3-sigma)
- V18: Reglas de negocio específicas (D10,D11,D17,D18,D19,D21)

**Resultados contra BD real (16,024 txs)**:
- 🔴 6 CRÍTICOS: V01 Retrocesión (1tx), V02 442 combos inválidos, V03 24 tipos inconsistentes, V05a 511 pares duplicados mismo banco, V08b 2 ingresos negativos, V18b 2 Wallapop|GASTO
- 🟡 7 ADVERTENCIAS: V07 500 sin merchant, V08a 146 gastos positivos, V10 1680 merchants sin cat1, V12 77 cat2 incorrectos, V15 9 importes cero, V16 10 nóminas anómalas, V17 36 outliers

**Integración**:
- `process_transactions.py`: lanza validación automáticamente al final, muestra resumen en logs
- CLI: `python3 validator.py [--since YYYY-MM] [--json] [--solo-criticas] [--checks V01 V05]`
- API: `from validator import run_validation; report = run_validation(db_path='finsense.db')`

**Archivos modificados**: `validator.py` (nuevo, 480 líneas), `process_transactions.py` (integración)

**Decisión Arquitectónica (D35)**: validator.py módulo independiente + integrado en process_transactions

---

### S66 — 2026-02-27 — FONDO CAPRICHOS + BLOQUE SEGUIMIENTO MENSUAL ✅

**Objetivo**:
Añadir al bot un bloque de datos de seguimiento mensual (presupuesto vs gasto real por categoría) y un sistema de "fondo de caprichos" que acumula el ahorro/exceso respecto a presupuesto en las categorías controlables.

**Presupuestos definidos e insertados** (6 categorías controlables):

| Cat1 | Presupuesto/mes | Media histórica |
|---|---|---|
| Alimentación | 425€ | 463€ |
| Restauración | 200€ | 211€ |
| Compras | 125€ | 327€ |
| Ropa y Calzado | 100€ | 141€ |
| Salud y Belleza | 75€ | 187€ |
| Ocio y Cultura | 50€ | 30€ |

**Tabla `fondo_caprichos` creada** en BD y en `create_db_tables()` de process_transactions.py.

**Nuevas funciones en `advisor.py`**:
- Constantes: `CATS_CONTROLABLES`, `ANIO_INICIO_FONDO=2026`, `MES_INICIO_FONDO=2`
- `get_presupuestos_controlables()` — lee presupuestos de BD
- `calcular_fondo_mes(anio, mes)` — calcula presupuesto vs real, UPSERT en fondo_caprichos
- `get_fondo_acumulado_anio(anio)` — suma diferencias de meses cerrados desde MES_INICIO_FONDO
- `get_bloque_seguimiento_mes()` — genera bloque texto para mensaje diario (✅/⚠️/❌ por cat + fondo acumulado)
- `get_bloque_fondo_mensual(anio, mes_cerrado)` — genera bloque detallado para cierre mensual

**`bot_telegram.py` modificado** — 4 puntos:
- Import: añadir `get_bloque_seguimiento_mes`, `get_bloque_fondo_mensual`
- `resumen_handler`: después del LLM, concatenar `get_bloque_seguimiento_mes()`
- `push_diario`: después del LLM, concatenar `get_bloque_seguimiento_mes()`
- `documento_handler`: después del LLM, concatenar `get_bloque_seguimiento_mes()`
- `push_mensual`: después del LLM, concatenar `get_bloque_fondo_mensual()`

**Output verificado con datos reales febrero 2026**:
- Bloque diario: Restauración ❌ 247€/200€ | Total 773€/975€ | Fondo: +0€ (desde este mes)
- Bloque mensual cierre: +202€ este mes (Ropa+100€, Salud+75€, Alim+57€, etc.)

**Verificación**: py_compile advisor.py ✅ | py_compile bot_telegram.py ✅ | Bloque generado con datos reales ✅

**Archivos modificados**: `advisor.py`, `bot_telegram.py`, `process_transactions.py`, `finsense.db`

**Decisiones Arquitectónicas (D33-D34)**:
- D33: Bloque datos se añade en bot_telegram DESPUÉS del LLM (LLM genera comentario, código añade datos)
- D34: Fondo caprichos en BD con 6 cats controlables, acumulado solo meses cerrados, excesos descuentan

---

### S65 — 2026-02-27 — ABANCA PARSER: SOPORTE FORMATO WEB/APP ✅

**Problema reportado**:
Usuario sube CSV de Abanca descargado desde web/app y el pipeline no lo reconoce. El formato nuevo usa separador coma (`,`) en vez de punto y coma (`;`) y tiene headers distintos: `Fecha,Concepto,Saldo,Importe,Fecha operación,Fecha valor`. Los importes llevan símbolo `€` y punto decimal: `-4025.0 €`.

**Diagnóstico**:
- `pipeline.py`: solo detectaba `'Fecha ctble;Fecha valor;Concepto'` como Abanca (formato banco directo)
- `parsers/abanca.py`: solo parseaba formato `;` (semicolon)
- Nuevo formato web/app tenía estructura completamente diferente

**Solución**:
1. **`pipeline.py`**: Añadir detección del formato web/app antes del Mediolanum check:
   ```python
   if first_line.startswith('Fecha,Concepto,Saldo,Importe'):
       return 'abanca'
   ```
2. **`parsers/abanca.py`**: Añadir `_detect_format()` que distingue `'semicolon'` vs `'comma'` leyendo la primera línea. Añadir `_parse_euro_amount()` para importes con `€`. El método `parse()` ramifica según formato detectado.

**Verificación**: CSV web/app procesado correctamente, txs insertadas en BD ✅

**Archivos modificados**: `parsers/abanca.py`, `pipeline.py`

**Decisión Arquitectónica (D32)**: AbancaParser soporta 2 formatos (semicolon banco directo + comma web/app)

---

## 📖 Historial Completo

Ver `HISTORIAL.md` para todas las sesiones S1–S64. El archivo nunca se compacta ni se borra.

Protocolo: al superar 3 sesiones, las más antiguas se mueven a HISTORIAL.md completas (sin resumir).
