# SESIONES.md — mis_finanzas_1.0

**Propósito**: Últimas 3 sesiones completadas (detalle operativo).

**Última actualización**: 2026-02-27 — Sesión 60 COMPLETADA

**Nota**: Estado mínimo, decisiones y pendientes → leer `ESTADO.md`

---

## 🟢 Últimas 3 Sesiones

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
