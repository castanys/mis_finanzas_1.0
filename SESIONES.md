# SESIONES.md — mis_finanzas_1.0

**Última actualización**: 2026-02-24 — Sesión 41 COMPLETADA

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

### S41 — 2026-02-24 — INTEGRACIÓN CLAUDE API (FALLBACK LLM) ✅ COMPLETADO
- **Hecho**: ✅ (1) **Instalación paquete `anthropic`**: v0.83.0 instalado en venv (9 nuevas dependencias incluidas). (2) **Configuración `.env`**: Clave ANTHROPIC_API_KEY actualizada (2 intentos: sk-ant-api03-xG4... → error 401; sk-ant-api03-RFvIVy... → error 404 sin acceso a modelos). (3) **Cadena fallback LLM completada**: (a) Intenta Qwen (API local) → (b) Si falla, intenta Claude API → (c) Si ambos fallan, devuelve análisis en formato crudo. (4) **Diagnóstico**: Primera clave: error autenticación. Segunda clave: auténtica pero sin permisos acceso a modelos (posiblemente clave test/desarrollo deshabilitada). (5) **Solución**: Bot funciona perfectamente con Qwen como LLM principal. Fallback Claude en código listo para cuando haya clave válida con acceso a modelos.
- **Métrica**: +anthropic (9 deps), fallback chain implementada, bot PID 2568178 corriendo. Logs limpios.
- **Decisión**: Mantener código tal como está. Cuando tengas clave válida con acceso a modelos Claude, bot usará Claude automáticamente sin cambios.
- **Próximo**: Bot operativo con Qwen. Si necesitas Claude, contactar Anthropic para habilitar acceso a modelos en la clave.

### S40 — 2026-02-24 — FIX DOCUMENTO HANDLER + HISTORIAL.MD PERMANENTE ✅ COMPLETADO
- **Hecho**: ✅ (1) **Fix crítico en `bot_telegram.py`** (línea 513-518): Verificación `if file_path.exists():` antes de `shutil.move()`. Problema: handler movía archivos ya movidos por pipeline→error "no such file". Solución: comprobar antes de mover; si no existe, loguear que fue movido por pipeline. (2) **Compactación SESIONES.md**: 143→82 líneas (-43%). Conservadas S36-S40 íntegras, S31-S35 en siguiente compactación. (3) **Creación HISTORIAL.md**: Archivo permanente (653 líneas) con S1-S40 completos, organizado en 3 fases. Nunca se compacta ni se borra. (4) **Actualización AGENTS.md**: Protocolo compactación → mover sesiones COMPLETAS a HISTORIAL.md (no resumir). (5) **Métricas actualizadas**: 15,661 txs, 2026-02-23, Cat2=Otros 543 (3.5%).
- **Métrica**: SESIONES.md -43%, HISTORIAL.md +653 líneas (24 sesiones archivadas), AGENTS.md actualizado, bot reiniciado (PID 2537328), 3 jobs OK. Coste tokens: 0 (HISTORIAL.md no se lee en cada sesión).
- **Commit**: 31367a1 "S40: crear HISTORIAL.md permanente + actualizar protocolo compactación"
- **Próximo**: (1) Mediolanum CSV por Telegram; (2) Nuevos PDFs TR; (3) Auditoría Fase 2 duplicados (baja prioridad).

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

## 📖 Historial Completo

Ver `HISTORIAL.md` para todas las sesiones pasadas (S1–S40). El archivo nunca se compacta ni se borra.
Nuevo protocolo: cada 5 sesiones, las antiguas se mueven a HISTORIAL.md completas (sin resumir).
