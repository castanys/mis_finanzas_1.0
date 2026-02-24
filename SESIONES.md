# SESIONES.md — mis_finanzas_1.0

**Última actualización**: 2026-02-24 — Sesión 40 EN PROGRESO

---

## 🔴 Decisiones Arquitectónicas (PERMANENTES — NO repetir)

Estas decisiones ya se tomaron. No volver a preguntar ni proponer alternativas.

| # | Decisión | Por qué | Sesión |
|---|----------|---------|--------|
| 1 | SQLite, no PostgreSQL | Proyecto local sin concurrencia | S1-2 |
| 2 | Taxonomía v2.2: Devoluciones como Cat2 | Cat2 dentro de cada GASTO, no Cat1 independiente | S3 |
| 3 | Clasificador 5 capas sin ML | Basado en reglas prioritarias + merchants + transfers + tokens | S1-2 |
| 4 | Reglas en classifier/, nunca BD | Correcciones en engine.py, merchants.py, tokens.py — reprocesar con reclassify_all.py | S1 |
| 5 | Idioma español | Todo código, comentarios, comunicación en español | S1 |
| 6 | Bitácora única SESIONES.md | Fuente de verdad centralizada, actualizar tras cada bloque | S9 |
| 7 | Inversión/Intereses → INGRESO/Intereses | Intereses cobrados son ingresos, no inversiones | S12 |
| 8 | Préstamos → Finanzas/Préstamos | Préstamos como Cat2 de Finanzas, no Cat1 independiente | S12 |

---

## 🟡 Estado Operativo

### Métricas Principales

| Métrica | Valor | Cómo verificar |
|---------|-------|----------------|
| Total transacciones | 15,661 | `sqlite3 finsense.db "SELECT COUNT(*) FROM transacciones;"` |
| Cat2=Otros | 543 | `sqlite3 finsense.db "SELECT COUNT(*) FROM transacciones WHERE cat2='Otros';"` |
| Cobertura clasificación | 96.5% (543 Otros = 3.5%) | 100% sin SIN_CLASIFICAR |
| Periodo cubierto | 2004-05-03 → 2026-02-23 | `sqlite3 finsense.db "SELECT MIN(fecha), MAX(fecha) FROM transacciones;"` |
| Bancos soportados | 7 | Openbank, MyInvestor, Mediolanum, Revolut, Trade Republic, B100, Abanca |
| Maestro CSV vigente | v29 (vigente S23-24, actualizar post-S40) | `validate/Validacion_Categorias_Finsense_MASTER_v29.csv` |
| Combinaciones Cat1\|Cat2 válidas | 188 | `classifier/valid_combos.py` |

### Pendientes Activos

**ALTA**:
- [x] REGLA #35: 6 txs "COMPRAS Y OPERACIONES CON TARJETA 4B" positivas → Compras/Devoluciones. ✅ COMPLETADA
- [x] REGLAS #36-#45: ~85 txs con keywords en merchant → categorías correctas. ✅ COMPLETADAS

**MEDIA**:
- [ ] Auditoría Fase 2 duplicados: Openbank (200 pares), Abanca (112 pares), B100 (51 pares) — BAJA prioridad

**BAJA**:
- [ ] Mediolanum: CSV cuando esté listo — bot procesará automáticamente

---

## 🟢 Últimas Sesiones (máx 5 — las anteriores van a ARCHIVO)

### S40 — 2026-02-24 — FIX DOCUMENTO HANDLER + COMPACTACIÓN 🔧
- **Hecho**: 🔧 (1) **Fix crítico en `bot_telegram.py`** (línea 513-518): Añadida verificación `if file_path.exists():` antes de `shutil.move()`. Problema: el handler intentaba mover archivos que ya había movido `process_transactions.py`, causando error "no such file or directory". Solución: comprobar si existe antes de mover; si no, loguear que fue movido por pipeline. (2) **Compactación de SESIONES.md**: Reducidas 239→~160 líneas (-33%). Conservadas sesiones S39, S38, S32, S31, S30 íntegras. Sesiones S16-S29 compactadas en "Resúmenes Compactados" (3-5 líneas cada). Métricas actualizadas: Total txs 14,821→15,661 (+840 del PDF TR), Período actualizado 2026-02-13→2026-02-23, Cat2=Otros: 380→543 (txs nuevas TR aún sin clasificación). (3) **Actualización AGENTS.md/REGLAS_PROYECTO.md**: sin cambios necesarios (ambos dentro de límites).
- **Métrica**: bot_telegram.py: +2 líneas (verificación existe), mejor manejo de errores. SESIONES.md: compactado -33%.
- **Próximo**: (1) Reiniciar bot; (2) Commit S40; (3) Esperar importación de Mediolanum y nuevos PDFs TR.

### S39 — 2026-02-24 — IMPORTACIÓN DE FICHEROS VÍA TELEGRAM ✅ COMPLETADO
- **Hecho**: ✅ SISTEMA DE IMPORTACIÓN DE DOCUMENTOS IMPLEMENTADO. (1) **Desactivado sync de pytr**: eliminadas líneas 301-332 en push_diario() — el CSV de TR está descartado, solo PDFs vía Telegram. (2) **Nuevo handler de documentos**: función `async def documento_handler()` (~130 líneas) que: (a) Verifica autorización (solo TELEGRAM_USER_ID), (b) Descarga PDF/CSV a input/, (c) Ejecuta process_transactions.py en background, (d) Parsea resultado para extraer nuevas_txs, (e) Notifica al usuario, (f) Archiva en input/procesados/. (3) **Registro del handler**: añadido `MessageHandler(filters.Document.ALL, documento_handler)` en main(). (4) **Actualización /ayuda**: sección "Importar documentos" con instrucciones. (5) **Pruebas**: bot reiniciado (PID 2531313), scheduler corriendo, logs OK. (6) **840 txs nuevas importadas** desde PDF TR completo.
- **Métrica**: +130 líneas handler. Bot funcional. BD: 15,661 txs.
- **Decisión**: Importación de documentos es único flujo entrada para PDFs/CSVs.

### S38 — 2026-02-24 — LIMPIEZA DE DUPLICADOS TR ✅ COMPLETADO
- **Hecho**: ✅ FASE 1 LIMPIEZA DUPLICADOS. (1) **Investigación**: 679 pares duplicados lógicos identificados. (2) **Ejecución**: Eliminadas 924 txs del CSV de S23. Carpeta `input/descartados/` creada con CSV movido. PDFs archivados en `input/archivo_tr/`. (3) **Resultado**: BD 15,745→14,821 txs (-924). TR: 187 txs solo de PDFs oficiales (cero contaminación).
- **Métrica**: 924 txs eliminadas. BD limpia.
- **Decisión**: CSV descartado definitivamente. TR usa solo PDFs.

### S35 — 2026-02-23 — BLOQUE 2: AUTOMATIZACIÓN TRADE REPUBLIC ✅
- **Hecho**: ✅ `sync_trade_republic.py` (395 líneas) + integración bot_telegram.py. Instalado pytr v0.4.6. Sync automático diario a las 12:00 con deduplicación correcta.
- **Métrica**: Bot corriendo (PID 2247104). 3 jobs programados. Tests: dry-run ✅, real ✅.

### S34 — 2026-02-23 — BLOQUE 3: SISTEMA 3-LEVEL DE MENSAJES ✅
- **Hecho**: ✅ SISTEMA 3-LEVEL IMPLEMENTADO. (1) **Daily (12:00)**: 8 ángulos aleatorios + 5 tonos rotativos. (2) **Monthly (día 1, 08:00)**: 3 ángulos rotativos. (3) **Annual (1 ene, 08:00)**: Revisión anual fija con proyección FIRE. Bot reiniciado (PID 2218166). Scheduler: 3 jobs registrados.
- **Métrica**: advisor.py: +560 líneas.

---

## 📦 Resúmenes Compactados

### S32 — 2026-02-23
PÁGINA 07 (GEOGRAFÍA) MEJORADA: Scattergeo → Scattermap con OpenStreetMap, filtrado merchants online (636→626 visibles), enriquecimiento masivo merchants (754→2,251), transacciones geolocalizadas +62% cobertura. Google Places API: ~1,500 llamadas (~15€).

### S31 — 2026-02-23
PÁGINA 07 VALIDADA: 516 líneas, componentes Streamlit (KPIs, mapa, tabla, PyDeck), funciones advisor.py OK, dependencias instaladas, tests OK, Streamlit arranca sin errores (localhost:8502).

### S30 — 2026-02-23
PROTOCOLO C+D IMPLEMENTADO: Regla #5 añadida en REGLAS_PROYECTO.md (prohibición explícita `UPDATE transacciones SET cat1/cat2`), AGENTS.md reescrito compacto (-38%), archivos dentro de límites. Opción C+D seleccionada.

### S29 — 2026-02-22
DASHBOARD GEOGRÁFICO IMPLEMENTADO: Función `get_resumen_geografico()` en advisor.py, página `07_🗺️_Geografía.py` creada, 4 KPIs (países, ciudades, gasto intl, % intl), mapa scatter_geo (burbujas) + PyDeck (puntos), 20 países, 26 ciudades.

### S28 — 2026-02-22
CAPA 2.5 CLASIFICADOR COMPLETADA: Mapeo `GOOGLE_TYPE_TO_CAT1_CAT2` implementado, lookup_merchant_from_db() en engine.py, Compras/Alojamiento eliminado (0 txs), 551 merchants con cat1 (+77%).

### S27 — 2026-02-22
ENRIQUECIMIENTO MASIVO MERCHANTS: extract_address_parts() mejorada, merchant_name poblado en 3,159→6,749 txs, fill_merchant_locations.py rellenó 734 merchants (98.4% cobertura city/country), 26 países.

### S26 — 2026-02-22
SISTEMA MERCHANTS + GEOGRAFÍA: Tabla merchants creada, 754 merchants migrados + 7 enriquecidos desde Google Places, merchant_name poblado, queries geográficas funcionales.

### S36 — 2026-02-23
BLOQUE 2: BUGS SYNC CORREGIDOS: 6 bugs críticos/medios arreglados (dedup, process_with_pipeline, --last_days, --output path, auth detection, output parsing). Usuario ejecutó `pytr login` exitosamente. End-to-end test: PDF descargado ✅, deduplicado correctamente ✅, 0 nuevas txs (ya en BD), bot reiniciado (PID 2367955).

### S25 — 2026-02-22
FASE A+B COMPLETADAS: Tablas presupuestos (6 variables) + cargos_extraordinarios (6 cargos 2026) pobladas, página `06_🎯_Presupuestos.py`, bot Telegram con advisor.py (análisis financiero), push 8:00 AM + comandos (/resumen, /presupuestos, /cargos, /ayuda), LLM fallback Qwen→Claude→prompt.

### S24 — 2026-02-22
CSV PYTR ANALIZADO Y DESCARTADO: 291 txs solapadas detectadas, CSV pytr pierde 11 intereses + 478 pagos con tarjeta vs histórico, 899 txs eliminadas de BD, archivos borrados, estrategia: PDFs mensuales (extracto oficial bancario).

### S23 — 2026-02-22
IMPORTACIÓN TRADE REPUBLIC: CSV pytr 899 txs (2025-02-28→2026-02-21) + PDF 88 txs (01-13 feb), total 987 nuevas, BD 15,548→16,535→15,661 (post-limpieza), Cat2=Otros 409→498→543, CSV maestro v29 generado.

### S22 — 2026-02-22
ANÁLISIS FINANCIERO NOV-ENE: Nómina 4.025€ estable, gastos estructurales ~938€/mes, ahorro neto ~3.087€/mes sin extraordinarios, CSV pytr compatible (914 txs), parser trade_republic_pytr.py integrado, corrección Energía XXI (Recibos/Luz→Recibos/Gas), Cat1 "Cuenta Común/Hogar" + REGLA #54 para Yolanda Arroyo (57 txs).

### S20 — 2026-02-22
FASE 2.2 MVP STREAMLIT: Estructura streamlit_app/{pages,components}, 4 páginas (app.py, 01_Resumen, 02_Evolución, 03_Categorías, 05_Recurrentes), componentes metrics.py + charts.py (Plotly), STREAMLIT_README.md documentado, validado imports + config.

### S19 — 2026-02-22
AUDITORÍA FASE 2.1: 15,548 txs verificadas, Cat2=Otros 409, CSV v27 validado, CSV v28 generado con 5 spot checks ✅, script generate_master_csv_v28.py creado.

### S18 — 2026-02-22
CLASIFICACIÓN EXHAUSTIVA 578 COMPRAS/OTROS: REGLAS #46-#53 (8 reglas) + 229 merchants implementados, reprocesamiento: Compras/Otros 578→353 (-38.9%), Cat2=Otros 582→409 (-29.7%), cobertura 97.7%.

### S17 — 2026-02-22
REGLAS #35-#45 IMPLEMENTADAS: 11 nuevas reglas en engine.py, Cat2=Otros 667→582 (-12.7%), Compras/Otros 663→578 (-12.8%).

### S16 — 2026-02-22
SISTEMA BITÁCORA V3: Reducción 1,517→221 líneas (-86%).

### Sesiones S1–S15 (compactado 2026-02-22)
Sistema base S1-S13: 7 parsers, BD 15,548 txs, 5-capas classifier, dedup SHA256, v2.2 taxonomy. Reducción Cat2=Otros S1-S13: 1,096→409 (-62.6%) via merchant extraction + reglas #1-#31. S14: Cripto cleanup. S15: 9 txs REGLAS #32-#34. Cobertura 100% SIN_CLASIFICAR, 97.7% global. LLM ask.py integrado (Ollama/Claude). Bitácora v3 implementada.

---

## 🔧 Historial de Cambios Recientes

- **S40 (HOY)**: Fix documento_handler, compactación SESIONES.md, métricas actualizadas
- **S39**: Handler importación documentos, desactivado sync pytr, 840 txs TR importadas
- **S38**: Fase 1 limpieza duplicados, CSV S23 descartado, 924 txs eliminadas
- **S35-36**: BLOQUE 2 completo + bugs sync corregidos, 6 fixes críticos/medios
- **S34**: BLOQUE 3 sistema 3-level de mensajes (daily/monthly/annual)
