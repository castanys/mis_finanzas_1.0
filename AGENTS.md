# AGENTS.md — Protocolo de Trabajo para mis_finanzas_1.0

---

## 🔴 REGLA CRÍTICA — Verificación pre-completado

Después de CUALQUIER bloque de trabajo:
1. **Verifica resultado**: test, query SQL, logs (no asumir "debería estar bien")
2. **Valida precisión**: número REAL verificado, no estimado
3. **Documenta**: Actualiza SESIONES.md (métricas + pendientes + entrada)
4. **Si fue decisión**: Añadir a Decisiones Arquitectónicas
5. **Si modificaste cat1/cat2**: PROHIBIDO UPDATE SQL. Ver Regla #5 en REGLAS_PROYECTO.md

**Excepción**: Si solo leíste/analizaste sin cambios, no actualices.

---

## Protocolo de Trabajo

### Inicio de sesión
1. Leer `ESTADO.md` (métricas + decisiones + pendientes, ~1.5K tokens)
2. Leer `SESIONES.md` (últimas 3 sesiones compactas, ~4K tokens)
3. Leer `REGLAS_PROYECTO.md` (reglas #1-#5, ~3K tokens)
4. Identificar pendiente o esperar instrucción

### Fin de bloque
1. Ejecutar verificación (query/test/logs)
2. Actualizar ESTADO.md: nuevas métricas + decisión (si la hay) + pendientes
3. Actualizar SESIONES.md: nueva entrada S[N] en formato compacto (4–5 líneas)
4. Commit: `git add ESTADO.md SESIONES.md && git commit -m "sesión [N]: descripción"`

### Escalado
Si bloque falla 2+ veces → PARAR. Documentar en SESIONES.md como BLOQUEADO. Pedir decisión.

---

## Protocolo de Rotación de Sesiones

**Límites**: ESTADO.md ≤50, SESIONES.md ≤120 (últimas 3 sesiones), AGENTS.md ≤80, REGLAS_PROYECTO.md ≤100

**Rotación automática**: 
1. Mantener siempre 3 sesiones en "Últimas Sesiones" de SESIONES.md
2. Al llegar a 4 sesiones, mover la más antigua a HISTORIAL.md (completa, sin resumir)
3. Commit: `git add ESTADO.md SESIONES.md HISTORIAL.md && git commit -m "compactar: sesión [N] → HISTORIAL.md"`

**Nota**: HISTORIAL.md es archivo permanente, nunca se compacta ni se borra.

---

## Comandos Principales

```bash
python3 reclassify_all.py              # Reprocesar con reglas actuales
python3 process_transactions.py         # Procesar nuevos CSVs
python3 ask.py "pregunta"              # Análisis LLM
sqlite3 finsense.db "SELECT ..."       # Verificar métricas BD
python3 test_parsers_manual.py         # Tests del clasificador
```

---

## Taxonomía de Referencia (23 Cat1)

**GASTO** (tipo='GASTO'): Alimentación, Compras, Deportes, Efectivo, Finanzas, Impuestos, Ocio y Cultura, Recibos, Restauración, Ropa y Calzado, Salud y Belleza, Seguros, Servicios Consultoría, Suscripciones, Transporte, Viajes, Vivienda

**INGRESO** (tipo='INGRESO'): Cashback, Intereses, Nómina, Wallapop

**OTROS** (tipo mixto): Liquidación, Transferencia, Inversión

**Regla**: NO crear Cat1 nuevas sin aprobación explícita. Ver REGLAS_PROYECTO.md #3.

---

## Idioma

Toda comunicación en **español**.
