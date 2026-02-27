# ESTADO.md — mis_finanzas_1.0

**Propósito**: Estado mínimo del proyecto — lo que todo agente debe saber antes de empezar una sesión.

**Última actualización**: 2026-02-27 — S66 COMPLETADA (fondo caprichos + bloque seguimiento mensual)

---

## 📊 Métricas Clave

| Métrica | Valor |
|---------|-------|
| **Total transacciones** | 16,020 |
| **SIN_CLASIFICAR** | 0 (100% cobertura) |
| **Período** | 2004-05-03 → 2026-02-23 |
| **Hashes únicos** | 15,999 (0 colisiones) |
| **Duplicados legítimos** | 249 txs (cargos provisionales + reversiones) |
| **Categorías Cat1** | 23 únicas |
| **Combinaciones Cat1\|Cat2** | 188 válidas |
| **Sesiones completadas** | 66 |
| **Merchants enriquecidos** | 824/846 (97.4% cobertura) |
| **Transacciones con merchant_name** | 6,917/16,020 (43.2%) |
| **Países únicos** | 27 |

---

## 🔴 Decisiones Arquitectónicas (D1–D24)

| # | Decisión | Por qué | Sesión |
|---|----------|---------|--------|
| 1 | SQLite local, no PostgreSQL | Proyecto sin concurrencia | S1-2 |
| 2 | Devoluciones = Cat2, no Cat1 | Subcategoría dentro de GASTO | S3 |
| 3 | Clasificador 5 capas sin ML | Basado en reglas prioritarias | S1-2 |
| 4 | Reglas en code, nunca BD directo | Reprocesar siempre con reclassify_all.py | S1 |
| 5 | Idioma español | Código, comentarios, comunicación | S1 |
| 6 | Bitácora única SESIONES.md | Fuente de verdad centralizada | S9 |
| 7 | Inversión/Intereses → INGRESO/Intereses | Intereses cobrados son ingresos | S12 |
| 8 | Préstamos → Finanzas/Préstamos | Cat2 de Finanzas, no Cat1 | S12 |
| 9 | Hash incluye `line_num` | Permite txs 100% idénticas en mismo fichero | S49 |
| 10 | AEAT/Devoluciones = INGRESO/Impuestos/IRPF | Decisión usuario, no GASTO | S51 |
| 11 | Mangopay + Wallapop = INGRESO/Wallapop | Ventas en plataforma son ingresos | S51 |
| 12 | Cat1 sin redundancia en Cat2 | Bizum vacío, no "Bizum P2P" | S51 |
| 13 | Restauración Cat2 = Otros | Unificación para subclasificaciones | S51 |
| 14 | NO normalizar tarjeta EN el hash | Hashes generados pre-normalizacion, mantener compatibilidad BD | S55 |
| 15 | `Intereses` = Cat1 propia, cat2 vacío | NO es Cat2 de Ingreso | S53 |
| 16 | `Ingreso` eliminada como Cat1 | Cashback recibe cashback/rewards | S53 |
| 17 | Revolut XXXX* = TRANSFERENCIA/Interna | Recargas Revolut son transferencias internas | S57 |
| 18 | NAMECHEAP/GitHub con exchange rate = Suscripciones | No son divisas aunque lleven $ en descripción | S57 |
| 19 | ORTONOVA (Clínica dental) = Salud y Belleza/Médico | Excluida de regla FARMAC/CLINIC genérica (S51→S58) | S58 |
| 20 | RESTAURANTE GRANADINA = Restauración/Otros | Excluida del refinamiento genérico de "Restaurante" | S58 |
| 21 | Devoluciones Amazon (importe>0) = Compras/Amazon | No son Compras/Devoluciones para análisis neto correcto | S58 |
| 22 | Bot envía análisis diario tras importar PDF | Genera resumen del día inmediatamente tras procesar (no espera push 12:00) | S59 |
| 23 | Modelo Claude para análisis = haiku-4-5 | Respuestas más rápidas, costo menor que sonnet | S60 |
| 24 | Restauración sin cat2 genérica | Todos RESTAURANTE/ARROCERIA → Otros (no agrupar genérico) | S60 |
| 25 | Análisis asesor siempre al importar | Enviar análisis tras importar PDF (incluso si nuevas_txs=0) | S61 |
| 26 | Tabla merchants con 13 columnas | Schema correcto: merchant_name, place_id, place_name, address, city, country, lat, lng, cat1, cat2, google_type, confidence, search_scope | S62 |
| 27 | Enriquecimiento Google Places automático | 824/846 merchants (97.4%) con datos geográficos (city, country, lat, lng) | S62 |
| 28 | merchant_name se propaga al clasificar y se guarda en BD | Pipeline completo: extract_merchant → classify() → pipeline → INSERT | S64 |
| 29 | Schema correcto en presupuestos y cargos_extraordinarios | Migrado en BD, actualizado create_db_tables() | S64 |
| 30 | Merchants nuevos se registran automáticamente | enrich_new_merchants() tras insertar txs nuevas | S64 |
| 31 | apply_recurrent_merchants se aplica en process_file() | Post-procesamiento en ambos process_file() y process_directory() | S64 |
| 32 | AbancaParser soporta formato web/app (separador coma) | Nuevo formato Abanca descarga web con headers Fecha,Concepto,Saldo,Importe | S65 |
| 33 | Bloque seguimiento mensual se añade en bot_telegram DESPUÉS del LLM | LLM genera comentario, código añade datos reales (LLM no los reescribe) | S66 |
| 34 | Fondo caprichos en BD (tabla fondo_caprichos) con 6 cats controlables | Presupuestos en BD, acumulado solo meses cerrados, excesos descuentan | S66 |

---

## 🟡 Pendientes Activos

| Prioridad | Tarea | Notas |
|-----------|-------|-------|
| BAJA | Auditoría Fase 2 duplicados | Openbank 200 pares, Abanca 112, B100 51 |
| BAJA | Enriquecimiento Google Places en background | Script enrich_background.py procesa merchants nuevos en background |

---

## ✅ Última Sesión

| Sesión | Fecha | Resultado | Cambios |
|--------|-------|-----------|---------|
| S66 | 2026-02-27 | ✅ COMPLETADA | Fondo caprichos: tabla fondo_caprichos, 6 presupuestos en BD, funciones advisor.py, bloque seguimiento en bot (3 puntos) + bloque cierre mensual |
| S65 | 2026-02-27 | ✅ COMPLETADA | AbancaParser: soporte formato web/app (separador coma, importes con €). Detection automática de formato en pipeline.py |
| S64 | 2026-02-27 | ✅ COMPLETADA | Arreglar 4 GAPs: (1) merchant_name se propaga y guarda en BD, (2) schema presupuestos/cargos_extraordinarios migrado, (3) merchants nuevos registrados automáticamente, (4) recurrent_merchants en process_file() |

---

## 🏛️ Canales de Información

- **ESTADO.md** (este archivo) — estado mínimo, se lee siempre (~1.5K tokens)
- **SESIONES.md** — últimas 3 sesiones detalladas (~120 líneas, ~4K tokens)
- **AGENTS.md** — protocolo de trabajo (~74 líneas, ~2.5K tokens)
- **REGLAS_PROYECTO.md** — restricciones arquitectónicas (~103 líneas, ~3K tokens)
- **HISTORIAL.md** — archivo permanente append-only (S1–S50, se lee si es necesario)

**Total lectura inicial**: ~11K tokens (estado + sesiones + protocolo + reglas)
