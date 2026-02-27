# SESIONES.md — mis_finanzas_1.0

**Propósito**: Últimas 3 sesiones completadas (detalle operativo).

**Última actualización**: 2026-02-27 — Sesión 64 COMPLETADA

**Nota**: Estado mínimo, decisiones y pendientes → leer `ESTADO.md`

---

## 🟢 Últimas 3 Sesiones

### S64 — 2026-02-27 — ARREGLO 4 GAPS CRÍTICOS DEL PIPELINE ✅

**Contexto**:
S63 completó auditoría exhaustiva del pipeline y encontró 4 GAPs críticos que impedían que el sistema funcionara correctamente. S64 los arregla todos.

**GAP 1 — CRÍTICO**: `merchant_name` NO se guardaba en BD
- **Problema**: Engine extraía merchant_name pero NO lo incluía en los returns de `classify()`
- **Solución**: 
  1. `engine.py`: mover extracción de merchant_name al inicio (línea 249) para que esté disponible en todos los returns
  2. Añadir `'merchant_name': merchant_name` a todos los 110 returns (script Python automatizado)
  3. `pipeline.py`: recoger merchant_name del resultado de clasificación
  4. `process_transactions.py`: incluir merchant_name en el INSERT
- **Resultado**: merchant_name se propaga correctamente: extract_merchant() → classify() → pipeline → BD INSERT

**GAP 2 — CRÍTICO**: Schema incorrecto en presupuestos y cargos_extraordinarios
- **Problema**: Schema antiguo no coincidía con lo que espera el código (advisor.py, bot_telegram.py, streamlit_app)
- **Solución**:
  1. Migración BD: DROP + CREATE con schema correcto (tablas estaban vacías)
  2. Actualizar `create_db_tables()` en process_transactions.py
  3. presupuestos: `cat1, cat2, importe_mensual, activo, updated_at`
  4. cargos_extraordinarios: `mes, dia, descripcion, importe_estimado, dias_aviso, activo, created_at`
- **Verificación**: Schema validado en BD, funciones advisor.py ahora funcionarán correctamente

**GAP 3 — MEDIO**: Merchants nuevos no se registraban automáticamente
- **Problema**: `enrich_unregistered_merchants.py` era manual, no se llamaba en pipeline
- **Solución**: Nueva función `enrich_new_merchants()` en process_transactions.py, llamada automáticamente después de INSERT
- **Resultado**: Merchants nuevos se registran automáticamente para posterior enriquecimiento con Google Places

**GAP 4 — MEDIO**: `apply_recurrent_merchants()` no se aplicaba en `process_file()`
- **Problema**: Post-procesamiento solo en `process_directory()`, no en `process_file()` (importar PDF individual)
- **Solución**: Mover llamada a `apply_recurrent_merchants()` a ambos métodos
- **Resultado**: Recurrent merchants se aplica tanto al procesar directorio como archivo individual

**Verificación**:
- ✅ Schema BD migrado y validado
- ✅ Código compila sin errores (py_compile)
- ✅ Tests de INSERT y clasificación con merchant_name
- ✅ Todos los 4 GAPs resueltos

**Commits**: `cb9aaffb` (sesión 64: arreglar 4 GAPs críticos del pipeline)

**Decisiones Arquitectónicas (D28-D31)**:
- D28: merchant_name se propaga al clasificar y se guarda en BD
- D29: Schema correcto en presupuestos y cargos_extraordinarios migrado
- D30: Merchants nuevos se registran automáticamente
- D31: apply_recurrent_merchants se aplica en process_file()

---

### S63 — 2026-02-27 — AUDITORÍA COMPLETA DEL PIPELINE ✅

**Objetivo**: Entender por qué el bot no procesaba merchants correctamente y encontrar todos los GAPs del sistema.

**Auditoría**:
1. Leí ESTADO.md, SESIONES.md, REGLAS_PROYECTO.md para contexto
2. Analicé flujo completo: pipeline.py → engine.py (5 capas) → merchants.py, recurrent_merchants.py, enrich_unregistered_merchants.py
3. Auditoreé toda la conectividad: clasificador → pipeline → process_transactions → BD
4. Verificué schemas BD vs código esperado

**Descubrimientos — 4 GAPs CRÍTICOS**:
1. **GAP 1 — CRÍTICO**: merchant_name extraído en engine pero NO se guarda en BD
2. **GAP 2 — CRÍTICO**: Schema presupuestos/cargos_extraordinarios es antiguo
3. **GAP 3 — MEDIO**: enrich_unregistered_merchants.py no está integrado en pipeline
4. **GAP 4 — MEDIO**: recurrent_merchants no se aplica en process_file()

**Resultado**: Documenté todos los gaps con impacto y soluciones propuestas. Esperar instrucción del usuario.

---

### S62 — 2026-02-27 — RECUPERACIÓN MERCHANTS + GOOGLE PLACES ✅

**Problema reportado**:
Usuario reporta que la tabla merchants estaba vacía y el bot no podía analizar con datos geográficos. El asesor necesita merchants enriquecidos para funciones como `get_merchants_para_mapa()` y `get_gastos_por_ubicacion()`.

**Diagnóstico**:
1. Tabla `merchants` con esquema incorrecto (3 columnas: id, nombre, categoria) vs 13 esperadas
2. Columna `merchant_name` en transacciones = NULL (todas 16,020 filas)
3. 846 merchants únicos no extraídos ni enriquecidos
4. Dashboard geográfico (página 07) sin datos

**Solución implementada**:
1. **Migrar esquema**: `ALTER TABLE merchants` → crear nueva tabla con 13 columnas correctas (merchant_name, place_id, place_name, address, city, country, lat, lng, cat1, cat2, google_type, confidence, search_scope)
2. **Poblar merchant_name**: 3,752 txs procesadas con `extract_merchant()`, 6,917/16,020 con merchant_name (43.2%)
3. **Insertar merchants**: 846 merchants únicos en tabla merchants
4. **Enriquecer Google Places**: `enrich_merchants.py` en background → 824/846 enriquecidos (97.4%), 0 errores, 22 no encontrados

**Verificación**:
- `sqlite3 finsense.db`: 6,917 txs con merchant_name, 824 merchants con place_id, 27 países únicos
- Dashboard ahora tiene datos geográficos (Spain 3,693 txs, Luxembourg 229, UK 49, etc.)
- Funciones `advisor.py` como `get_merchants_para_mapa()`, `get_gastos_por_ubicacion()` ahora funcionan

**Commits**: Pendiente (se hace después)

**Decisiones Arquitectónicas (D26-D27)**:
- D26: Tabla merchants con 13 columnas correctas (esquema coherente con enriquecimiento Google Places)
- D27: Enriquecimiento automático Google Places para todos los merchants únicos (97.4% cobertura)

---

### S61 — 2026-02-27 — FIX BOT: ANÁLISIS ASESOR SIEMPRE AL IMPORTAR PDF ✅

**Problema reportado**:
Usuario no recibía mensaje del asesor financiero tras subir PDFs. Cuando subía nuevos extractos, el bot decía "0 nuevas transacciones" pero no enviaba el análisis del asesor.

**Diagnóstico**:
- Condición antigua: `if result.returncode == 0 and nuevas_txs > 0:` solo dispara análisis si hay txs nuevas
- Problema: PDFs duplicados (mismo contenido que ya estaba en BD) → `nuevas_txs = 0` → sin análisis
- Usuario espera: análisis siempre tras importar (aunque no haya txs nuevas)

**Solución**:
- `bot_telegram.py:639` → cambiar condición a `if result.returncode == 0:` (sin AND nuevas_txs)
- Ahora: análisis se envía siempre que el PDF procese correctamente

**Verificación**:
- `py_compile bot_telegram.py` ✅
- `systemctl --user restart mis_finanzas_bot` ✅ (PID 1492306 activo)
- Logs: bot corriendo con nuevo código

**Commit**: (pendiente git add/commit)

**Decisión Arquitectónica (D25)**: Análisis asesor siempre al importar PDF

---

### S60 — 2026-02-27 — 3 FIXES USUARIO: MODELO CLAUDE + RESTAURACIÓN/OTROS ✅

**Problemas reportados**:
1. Bot envía análisis crudo sin LLM (API key no usada)
2. Categoría Restauración/Restaurante no aporta valor (197 txs genéricas)
3. Modelo Claude sonnet lento para push automático

**Solución**:
1. **Modelo Claude**: `bot_telegram.py:119` → cambiar `claude-3-5-sonnet-20241022` a `claude-haiku-4-5` (más rápido, costo menor)
2. **Restauración/Otros**: 
   - `engine.py:35` → `refine_cat2_by_description` devuelve Otros (no Restaurante)
   - `engine.py:599` → REGLA #38 cambiar `cat2_refined = refine_cat2_by_description("Restauración", "Otros", ...)`
3. **Reclassify**: `reclassify_all.py` → 197 txs Restauración/Restaurante → Restauración/Otros

**Verificación**:
- `reclassify_all.py` ✅ (197 txs reclasificadas)
- `process_transactions.py` ✅ (0 nuevas, 16,012 total)
- `systemctl --user restart mis_finanzas_bot` ✅ (bot con nuevo modelo activo)

**Commits**: `89d8747c` (fix: 3 cambios — modelo Claude + Restauración/Otros)

**Decisiones Arquitectónicas (D23-D24)**:
- D23: Modelo Claude = haiku-4-5 (respuestas rápidas, costo menor)
- D24: Restauración sin cat2 genérica (todos RESTAURANTE/ARROCERIA → Otros)

---

### S59 — 2026-02-27 — ENHANCEMENT BOT: ANÁLISIS DIARIO + SERVICIO SYSTEMD ✅

**Objetivo**: 1) Mejorar UX: análisis diario tras importar PDF, 2) Bot permanente: servicio systemd, 3) Documentar servicios del proyecto

**Cambios**:
1. **Análisis diario**: `bot_telegram.py:documento_handler` — generar + enviar resumen del día si `nuevas_txs > 0`
2. **Servicio systemd**: `~/.config/systemd/user/mis_finanzas_bot.service` — bot corriendo permanente, reinicia automático en caso de fallo
3. **loginctl enable-linger**: Servicio sobrevive sin sesión abierta
4. **SERVICIOS.md**: Documentación centralizada a nivel `/home/pablo/apps/` con:
   - Guía completa bot (comandos systemd, logs, troubleshooting)
   - Guía dashboard Streamlit (manual bajo demanda)
   - Scheduler interno APScheduler (push diario/mensual/anual)
   - Tabla referencia rápida
   - Estructura para otros proyectos

**Verificación**:
- `py_compile bot_telegram.py` ✅
- `systemctl --user status mis_finanzas_bot` ✅ (running)
- PDF procesado: `Extracto de cuenta.pdf` → importado + análisis enviado ✅
- `loginctl show-user pablo | grep Linger` → Linger=yes ✅

**Commits**: `c0f6a9c6` (feat: análisis diario tras PDF), `c4a063db` (docs: ESTADO.md + SESIONES.md S59), `61d5976c` (feat: procesamiento exitoso PDF via systemd)

**Decisión Arquitectónica (D22)**: Bot envía análisis diario tras importar PDF

---

### S58 — 2026-02-26 — 3 FIXES USUARIO: ORTONOVA, GRANADINA, AMAZON ✅

**Problemas reportados**:
1. CLINICA ORTONOVA (Apple Pay): sigue siendo Farmacia, debería ser Médico/Dental (3 txs)
2. RESTAURANTE GRANADINA: sigue siendo Restaurante, usuario pide quitar ese cat2 (1 tx)
3. Devoluación Amazon id=15694: en cat2=Devoluciones, debería estar en Compras para análisis neto correcto

**Diagnóstico**:
- ORTONOVA: REGLA #31 (Capa 0) clasifica "COMPRA EN" + "CLINIC" como Farmacia antes de merchants.py que tiene Médico
- GRANADINA: refine_cat2_by_description() detecta palabra "RESTAURANTE" y sobreescribe a Restaurante
- Amazon: importe positivo (devolución) → cat2=Devoluciones separa del análisis Compras/Amazon (neto negativo)

**Solución**:
- Fix 1: engine.py:515 excluir ORTONOVA de regla FARMAC/CLINIC → baja a merchants.py (Médico)
- Fix 2: engine.py:34 excluir GRANADINA del refinamiento de "Restaurante" → queda Otros
- Fix 3: engine.py:289-297 cambiar Amazon refunds: cat2=Devoluciones → cat2=Amazon
- Extra: merchants.py:160 cambiar ORTONOVA cat2 Dental → Médico (consistencia Google Places)

**Verificación**: reclassify_all.py ✅ + process_transactions.py (0 nuevas en TODOS ficheros) ✅ | 15,999 txs

**Commits**: `f37f5461`

**Impacto**:
- ORTONOVA: 3 txs Farmacia → Médico ✅
- GRANADINA: 1 tx Restaurante → Otros ✅
- Amazon devoluciones: 14 txs Compras/Devoluciones → Compras/Amazon ✅

---

## 📖 Historial Completo

Ver `HISTORIAL.md` para todas las sesiones S1–S57. El archivo nunca se compacta ni se borra.

Protocolo: cada 5 sesiones, las más antiguas se mueven a HISTORIAL.md completas (sin resumir).
