# ESTADO.md — mis_finanzas_1.0

**Propósito**: Estado mínimo del proyecto — lo que todo agente debe saber antes de empezar una sesión.

**Última actualización**: 2026-02-25 — S53 COMPLETADA

---

## 📊 Métricas Clave

| Métrica | Valor |
|---------|-------|
| **Total transacciones** | 15,993 |
| **SIN_CLASIFICAR** | 0 (100% cobertura) |
| **Período** | 2004-05-03 → 2026-02-23 |
| **Hashes únicos** | 15,993 (0 colisiones) |
| **Duplicados legítimos** | 249 txs (cargos provisionales + reversiones) |
| **Categorías Cat1** | 23 únicas |
| **Combinaciones Cat1\|Cat2** | 188 válidas |
| **Sesiones completadas** | 53 |

---

## 🔴 Decisiones Arquitectónicas (D1–D16)

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
| 14 | Tarjeta normalizada antes del hash | `****XXXX` para deduplicación cross-file | S51 |
| 15 | `Intereses` = Cat1 propia, cat2 vacío | NO es Cat2 de Ingreso | S53 |
| 16 | `Ingreso` eliminada como Cat1 | Cashback recibe cashback/rewards | S53 |

---

## 🟡 Pendientes Activos

| Prioridad | Tarea | Notas |
|-----------|-------|-------|
| BAJA | Enmascarar tarjetas en Abanca, B100 | Fase 2 — solo Openbank hecho (S51) |
| BAJA | Auditoría Fase 2 duplicados | Openbank 200 pares, Abanca 112, B100 51 |

---

## ✅ Última Sesión

| Sesión | Fecha | Resultado | Cambios |
|--------|-------|-----------|---------|
| S53 | 2026-02-25 | ✅ COMPLETADA | Saneamiento bitácora + correcciones clasificador |

---

## 🏛️ Canales de Información

- **ESTADO.md** (este archivo) — estado mínimo, se lee siempre (~1.5K tokens)
- **SESIONES.md** — últimas 3 sesiones detalladas (~120 líneas, ~4K tokens)
- **AGENTS.md** — protocolo de trabajo (~74 líneas, ~2.5K tokens)
- **REGLAS_PROYECTO.md** — restricciones arquitectónicas (~103 líneas, ~3K tokens)
- **HISTORIAL.md** — archivo permanente append-only (S1–S50, se lee si es necesario)

**Total lectura inicial**: ~11K tokens (estado + sesiones + protocolo + reglas)
