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
1. Leer `SESIONES.md` (decisiones + estado actual)
2. Leer `REGLAS_PROYECTO.md` (reglas #1-#5)
3. Identificar pendiente o esperar instrucción

### Fin de bloque
1. Ejecutar verificación (query/test/logs)
2. Actualizar SESIONES.md: métrica nueva + pendiente marcado + entrada S[N]
3. Commit: `git add SESIONES.md && git commit -m "sesión [N]: descripción"`

### Escalado
Si bloque falla 2+ veces → PARAR. Documentar en SESIONES.md como BLOQUEADO. Pedir decisión.

---

## Compactación de SESIONES.md (cada 5 sesiones)

1. Dejar solo últimas 5 sesiones en "Últimas Sesiones"
2. **Mover sesiones antiguas COMPLETAS a HISTORIAL.md** (sin resumir, sin cortar)
3. Eliminar secciones "Resúmenes Compactados" y "Historial de Cambios Recientes" de SESIONES.md
4. Commit: `git add SESIONES.md HISTORIAL.md && git commit -m "compactar: sesiones [rango] → HISTORIAL.md"`

**Nota**: HISTORIAL.md es archivo permanente, nunca se compacta ni se borra.

Límites: SESIONES.md ≤150, AGENTS.md ≤80, REGLAS_PROYECTO.md ≤100 líneas, HISTORIAL.md sin límite.

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
