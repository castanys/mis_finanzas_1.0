# ESTADO.md — mis_finanzas_1.0

**Propósito**: Estado mínimo del proyecto — lo que todo agente debe saber antes de empezar una sesión.

**Última actualización**: 2026-02-26 — S58 COMPLETADA (3 fixes usuario)

---

## 📊 Métricas Clave

| Métrica | Valor |
|---------|-------|
| **Total transacciones** | 15,999 |
| **SIN_CLASIFICAR** | 0 (100% cobertura) |
| **Período** | 2004-05-03 → 2026-02-23 |
| **Hashes únicos** | 15,999 (0 colisiones) |
| **Duplicados legítimos** | 249 txs (cargos provisionales + reversiones) |
| **Categorías Cat1** | 23 únicas |
| **Combinaciones Cat1\|Cat2** | 188 válidas |
| **Sesiones completadas** | 55 |

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
| 14 | NO normalizar tarjeta EN el hash | Hashes generados pre-normalizacion, mantener compatibilidad BD | S55 |
| 15 | `Intereses` = Cat1 propia, cat2 vacío | NO es Cat2 de Ingreso | S53 |
| 16 | `Ingreso` eliminada como Cat1 | Cashback recibe cashback/rewards | S53 |
| 17 | Revolut XXXX* = TRANSFERENCIA/Interna | Recargas Revolut son transferencias internas | S57 |
| 18 | NAMECHEAP/GitHub con exchange rate = Suscripciones | No son divisas aunque lleven $ en descripción | S57 |
| 19 | ORTONOVA (Clínica dental) = Salud y Belleza/Médico | Excluida de regla FARMAC/CLINIC genérica (S51→S58) | S58 |
| 20 | RESTAURANTE GRANADINA = Restauración/Otros | Excluida del refinamiento genérico de "Restaurante" | S58 |
| 21 | Devoluciones Amazon (importe>0) = Compras/Amazon | No son Compras/Devoluciones para análisis neto correcto | S58 |

---

## 🟡 Pendientes Activos

| Prioridad | Tarea | Notas |
|-----------|-------|-------|
| BAJA | Auditoría Fase 2 duplicados | Openbank 200 pares, Abanca 112, B100 51 |

---

## ✅ Última Sesión

| Sesión | Fecha | Resultado | Cambios |
|--------|-------|-----------|---------|
| S58 | 2026-02-26 | ✅ COMPLETADA | 3 fixes usuario: ORTONOVA (3 txs Farmacia→Médico), GRANADINA (1 tx Restaurante→Otros), Amazon devol. (14 txs Compras/Devoluciones→Compras/Amazon) |

---

## 🏛️ Canales de Información

- **ESTADO.md** (este archivo) — estado mínimo, se lee siempre (~1.5K tokens)
- **SESIONES.md** — últimas 3 sesiones detalladas (~120 líneas, ~4K tokens)
- **AGENTS.md** — protocolo de trabajo (~74 líneas, ~2.5K tokens)
- **REGLAS_PROYECTO.md** — restricciones arquitectónicas (~103 líneas, ~3K tokens)
- **HISTORIAL.md** — archivo permanente append-only (S1–S50, se lee si es necesario)

**Total lectura inicial**: ~11K tokens (estado + sesiones + protocolo + reglas)
