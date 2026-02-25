# REVISION_OPUS.md — Análisis del Sistema de Bitácora

**Audiencia**: Opus (modelo externo para revisión arquitectónica)

**Objetivo**: Evaluar eficiencia del sistema de bitácora, consumo de tokens, y proponer mejoras

**Fecha**: 2026-02-25

---

## A. Contexto del Proyecto

### Resumen Ejecutivo

Sistema de finanzas personales automatizado (`mis_finanzas_1.0`):
- **Propósito**: Clasificar y organizar 15+ años de movimientos bancarios
- **Estado actual**: 15,993 transacciones, 0% sin clasificar, 100% automatizado
- **Stack**: Python 3 (parsers + clasificador), SQLite (BD), 23 categorías de gasto

### Métricas Clave

| Métrica | Valor | Contexto |
|---------|-------|----------|
| **Total transacciones** | 15,993 | Integración de 9 bancos (Openbank, Trade Republic, MyInvestor, Mediolanum, Revolut, Bankinter, B100, Abanca, Enablebanking) |
| **Período cubierto** | 2004-05-03 → 2026-02-23 | 22 años de historial completo |
| **Categorías Cat1** | 23 únicas | 17 gastos, 4 ingresos, 2 otros |
| **Categorías Cat2** | 188 combinaciones válidas | cat1\|cat2 pairs en valid_combos.py |
| **Sin clasificar** | 0 (0%) | 100% de cobertura conseguida en S50 |
| **Duplicados detectados** | 249 txs | Legítimos: cargos provisionales + reversiones (no son errores) |
| **Sesiones completadas** | 53 | Desde S1 hasta S53 (2026-02-25) |
| **Decisiones arquitectónicas documentadas** | 16 (D1–D16) | Permanentes, no se repiten |

### Evolución Principal

```
S1–S15: Base sistema + 21 categorías iniciales
S16–S29: Clasificación exhaustiva (Otros: 1,096→409 txs)
S30–S48: Auditoría y refinamiento
S49–S53: Fix críticos (deduplicación, consistencia BD, clasificador)

Resultado final: 15,993 txs clasificadas, 0 SIN_CLASIFICAR ✅
```

---

## B. Sistema de Bitácora — Análisis Detallado

### B.1 Arquitectura Actual

El proyecto usa un sistema de 4 archivos para documentación:

#### 1. **AGENTS.md** (74 líneas)
```
Propósito: Protocolo de trabajo para agentes
Contenido:
  - Regla crítica de verificación pre-completado
  - Protocolo de inicio/fin de sesión
  - Protocolo de escalado (falla 2+)
  - Protocolo de compactación cada 5 sesiones
  - Comandos principales (reclassify_all.py, ask.py, etc.)
  - Taxonomía de referencia (23 Cat1)
Límite: 80 líneas
Estado: ✅ En límite (74 líneas)
```

#### 2. **REGLAS_PROYECTO.md** (103 líneas)
```
Propósito: Restricciones arquitectónicas del proyecto
Contenido:
  - Regla #1: Nunca parchear, siempre arreglar (no UPDATE directo de BD)
  - Regla #2: Nunca inventar datos (todo debe ser verificable)
  - Regla #3: Taxonomía cerrada (no crear Cat1 sin aprobación)
  - Regla #4: Verificación obligatoria (query SQL antes de completar)
  - Regla #5: Prohibición UPDATE directo de cat1/cat2
  - Regla #6: DELETE directo permitido solo para duplicados verificados
Límite: 100 líneas
Estado: ✅ En límite (103 líneas)
```

#### 3. **SESIONES.md** (232 líneas)
```
Propósito: Bitácora activa (fuente de verdad operativa)
Contenido:
  - Decisiones arquitectónicas permanentes (D1–D16)
  - Métricas principales (txs totales, duplicados, período)
  - Pendientes activos (con prioridad ALTA/BAJA)
  - Últimas 5 sesiones detalladas (S49–S53)
  - Referencia a HISTORIAL.md para sesiones antiguas
Límite: 150 líneas
Estado: ⚠️ FUERA DE LÍMITE (232 líneas, +82 líneas sobre límite)
Razón: Las 5 sesiones últimas (S49–S53) son muy detalladas (~30–40 líneas cada una)
```

#### 4. **HISTORIAL.md** (~760 líneas)
```
Propósito: Archivo permanente append-only (sin límite)
Contenido: Todas las sesiones completadas (S1–S47) en texto completo
Acceso: NO se carga en contexto operativo (consume demasiados tokens)
Estado: ✅ Funcionando correctamente, S48–S53 aún en SESIONES.md (para acceso rápido)
```

### B.2 El Flujo de Lectura Actual

**Antes de cada sesión, el agente lee**:
1. AGENTS.md (74 líneas) — 2–3K tokens
2. REGLAS_PROYECTO.md (103 líneas) — 2–3K tokens
3. SESIONES.md (232 líneas) — 5–7K tokens
4. **NO lee HISTORIAL.md** (demasiado costoso, 760 líneas = 15–20K tokens)

**Consumo por lectura inicial**: ~9–13K tokens

**Problema**: Aunque SESIONES.md está "compactada", sigue siendo demasiado grande porque:
- Las 5 sesiones últimas ocupan todo el espacio (S49: 20 líneas, S50: 14 líneas, S51: 25 líneas, S52: 38 líneas, S53: 46 líneas)
- El usuario quería un máximo de 150 líneas = ~5 sesiones cortas, pero sesiones complejas = 30–40 líneas cada una

### B.3 Compactación: El Protocolo vs la Realidad

**Protocolo establecido** (en AGENTS.md, líneas 35–44):
```
Cada 5 sesiones:
1. Dejar solo últimas 5 sesiones en "Últimas Sesiones"
2. Mover sesiones antiguas COMPLETAS a HISTORIAL.md
3. Commit
Límites: SESIONES.md ≤150, AGENTS.md ≤80, REGLAS_PROYECTO.md ≤100
```

**Lo que ha pasado**:
- S1–S47 movidas a HISTORIAL.md ✅ (sesión S53)
- Quedan S49–S53 en SESIONES.md = 232 líneas
- Limitación: incluso 4–5 sesiones complejas superan 150 líneas

**Tensión identificada**: El límite 150 líneas es apropiado para sesiones cortas (5–10 líneas), pero las sesiones de S49–S53 son inherentemente largas porque:
- S49: Fix crítico (afecta 7 parsers)
- S50: Limpieza masiva + 100% clasificación
- S51: 11 correcciones del usuario
- S52: 2 fixes + bitácora
- S53: Compactación + correcciones

---

## C. Impacto en Consumo de Tokens

### C.1 Análisis de Lectura Inicial

**Escenario A: Sesión típica**

```
Inicio sesión:
  AGENTS.md (74 líneas)              ~2.5K tokens
  REGLAS_PROYECTO.md (103 líneas)    ~3K tokens
  SESIONES.md (232 líneas)           ~7K tokens
  ─────────────────────────────────
  Total lectura inicial               ~12.5K tokens (8% del presupuesto Haiku)

Trabajo efectivo:
  Búsqueda codebase (~5–10 archivos)  ~3–5K tokens
  Edición + verificación              ~5–10K tokens
  Commit + documentación              ~2–3K tokens
  ─────────────────────────────────
  Total trabajo                       ~10–18K tokens

TOTAL POR SESIÓN: 22.5–30.5K tokens
```

### C.2 Comparativa: Costo de Lectura vs Beneficio

| Componente | Líneas | Tokens | ¿Se lee? | Frecuencia | Eficiencia |
|------------|--------|--------|----------|-----------|-----------|
| AGENTS.md | 74 | ~2.5K | Siempre | Cada sesión | ✅ Alta — necesario para protocolo |
| REGLAS_PROYECTO.md | 103 | ~3K | Siempre | Cada sesión | ✅ Alta — crítico (6 reglas fundamentales) |
| SESIONES.md | 232 | ~7K | Siempre | Cada sesión | ⚠️ Media — 40% de contenido es 5 sesiones complejas |
| HISTORIAL.md | 760 | ~20K | Nunca | N/A | ❌ Baja — demasiado costoso para lectura, solo write |

### C.3 Simulación: Impacto de Cambios Propuestos

**Opción A: Reducir SESIONES.md a 3 sesiones en lugar de 5**
```
Estado actual: SESIONES.md = 232 líneas (S49–S53)
Propuesta: SESIONES.md = 140 líneas (S51–S53 solo)

Tokens ahorrados por lectura: ~3–4K tokens
Frecuencia: cada sesión
Impacto anual (52 sesiones): ~156–208K tokens ahorrados

Costo: Perder acceso rápido a S49–S50 (pero están en HISTORIAL.md)
```

**Opción B: Separar "estado mínimo" en archivo compacto (ESTADO.md)**
```
Crear archivo de solo 20–30 líneas con:
  - Total txs + SIN_CLASIFICAR
  - Únicas decisiones sin documentación reciente (D1–D8)
  - Pendientes activos SOLO (máx 5 items)
  
Tokens ahorrados por lectura: ~2–3K tokens
Costo: Overhead de leer 2 archivos (mínimo)
Beneficio: SESIONES.md queda para historial detallado
```

**Opción C: Log append-only (propuesto en pregunta 1)**
```
Crear LOG_ANALISIS.md (no se lee en contexto)
Sirve solo para análisis externo (Opus, etc.)

Tokens ahorrados: 0 (no entra en lectura inicial)
Beneficio: Permite detectar patrones sin contaminar contexto operativo
```

---

## D. Preguntas para Opus

### D.1 Diseño de Bitácora

**Pregunta 1**: ¿El diseño actual (4 archivos) es óptimo para minimizar tokens?

Alternativas consideradas:
- (A) Consolidar todo en 1 archivo (no, se inflaría)
- (B) Expandir a 5–6 archivos especializados (ej: ESTADO.md, CAMBIOS.md, LOGS.md)
- (C) Mantener 4 pero optimizar contenido de cada uno

**Pregunta 2**: ¿Tiene sentido el límite de 150 líneas para SESIONES.md cuando las 5 sesiones últimas ocupan 232?

Opciones:
- Reducir a 3 sesiones (140 líneas) vs 5 sesiones (232 líneas)
- Aceptar que sesiones complejas = más líneas (ajustar límite a 200–250)
- Abstraer sesiones complejas a una estructura más compacta

### D.2 Estructura Mínima de Estado

**Pregunta 3**: ¿Cuál es el estado mínimo que un agente nuevo necesita para empezar una sesión sin perder contexto?

Candidatos:
```
Mínimo absoluto:
  - Total txs + SIN_CLASIFICAR
  - Última decisión arquitectónica (D16)
  - Pendientes activos ÚNICO

Deseable:
  + Últimas 2 sesiones (resultados)
  + Últimas 3 decisiones (D14–D16)
  + Métrica de "salud" (hashes únicos, colisiones)
```

**Pregunta 4**: ¿Vale la pena mantener un log append-only separado (LOG_ANALISIS.md) para análisis externo sin comprometer contexto operativo?

Ventajas:
- Cero overhead en lectura inicial (no se carga)
- Permite detectar patrones (velocidad, bloqueos, tipos de tarea)
- Auditoría transparente de progreso

Desventajas:
- Overhead de escritura (append) al final de cada sesión
- Requiere gestión manual (no se auto-prune)

---

## E. Datos del Proyecto — Snapshot S53

### E.1 Base de Datos

```sql
-- Esquema
CREATE TABLE transacciones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fecha TEXT NOT NULL,
  importe REAL NOT NULL,
  descripcion TEXT NOT NULL,
  banco TEXT NOT NULL,
  cuenta TEXT,
  tipo TEXT,
  cat1 TEXT,
  cat2 TEXT,
  hash TEXT UNIQUE NOT NULL,
  source_file TEXT,
  merchant_name TEXT
);

-- Métricas actuales
Total: 15,993 transacciones
Período: 2004-05-03 → 2026-02-23 (22 años)
SIN_CLASIFICAR: 0 (100% cobertura)
Hashes únicos: 15,993 (0 colisiones)
Duplicados legítimos detectados: 249 txs (cargos provisionales + reversiones)
```

### E.2 Distribución por Banco

| Banco | Txs | % | Origen |
|-------|-----|---|--------|
| Openbank | 13,745 | 86% | CSV + API Enablebanking |
| Trade Republic | 969 | 6% | PDF extracto |
| Mediolanum | 457 | 3% | XLS extracto |
| Revolut | 210 | 1% | CSV |
| MyInvestor | 171 | 1% | CSV |
| Bankinter | 149 | 1% | CSV |
| B100 | 148 | 1% | CSV |
| Abanca | 145 | 1% | CSV |

### E.3 Distribución por Tipo

| Tipo | Txs | % |
|------|-----|---|
| GASTO | 12,865 | 80.4% |
| INGRESO | 1,321 | 8.3% |
| TRANSFERENCIA | 1,807 | 11.3% |

### E.4 Top 10 Categorías (Cat1)

| Categoría | Txs | % | Tipo |
|-----------|-----|---|------|
| Compras | 3,006 | 18.8% | GASTO |
| Interna | 2,712 | 17.0% | TRANSFERENCIA |
| Alimentación | 1,754 | 11.0% | GASTO |
| Efectivo | 1,229 | 7.7% | GASTO |
| Transporte | 1,120 | 7.0% | GASTO |
| Restauración | 1,023 | 6.4% | GASTO |
| Bizum | 890 | 5.6% | TRANSFERENCIA |
| Impuestos | 294 | 1.8% | GASTO |
| Viajes | 264 | 1.7% | GASTO |
| Finanzas | 252 | 1.6% | GASTO |

### E.5 Evolución de Cobertura

```
S1–S15:   1,096 Otros (7.0%) → Fase inicial
S16–S29:   582 Otros (3.7%) → Clasificación exhaustiva
S30–S47:   409 Otros (2.6%) → Auditoría y refinamiento
S48–S50:     0 Otros (0.0%) → 100% cobertura (S50: 0 SIN_CLASIFICAR)
S51–S53:     0 Otros (0.0%) → Mantenimiento
```

---

## F. Recomendaciones Preliminares (sin esperar Opus)

### F.1 Inmediatas (próxima sesión)

1. **Compactar SESIONES.md a 3 sesiones** (S51–S53)
   - Mover S49–S50 a HISTORIAL.md
   - Ahorro: ~3–4K tokens por lectura inicial

2. **Crear LOG_ANALISIS.md** (ya hecho)
   - Append-only, no se lee en contexto
   - Permite análisis externo

### F.2 Mediano plazo (próximas 5 sesiones)

3. **Extraer "ESTADO.md" compacto** (~30 líneas)
   - Métricas mínimas (txs, SIN_CLASIFICAR)
   - Decisiones recientes (últimas 5: D12–D16)
   - Pendientes activos (máx 5)

4. **Auditar overhead de Git**
   - Ejecutar `git prune` (objetos sueltos)
   - Limpiar raíz (89 archivos, muchos artefactos)

### F.3 Largo plazo (después de feedback Opus)

5. **Rediseñar lectura inicial según recomendaciones**
   - Optimizar tokens sin perder contexto
   - Ajustar límites de líneas según complejidad real

---

## G. Métricas Esperadas de Respuesta de Opus

Esperamos que Opus analice y responda sobre:

1. **Eficiencia del diseño** (escala 1–10)
2. **Riesgo de pérdida de contexto** si reducimos SESIONES.md
3. **Mejor estructura de estado mínimo** (propuesta concreta)
4. **ROI de LOG_ANALISIS.md** (¿vale la pena?)
5. **Recomendaciones de límites de líneas** (SESIONES.md, AGENTS.md, etc.)
6. **Pattern analysis** de LOG_ANALISIS.md (velocidad por sesión, tipos de tarea, etc.)

---

**Archivos adjuntos a Opus**:
- [ ] Este documento (REVISION_OPUS.md)
- [ ] SESIONES.md (estado actual)
- [ ] AGENTS.md (protocolo)
- [ ] REGLAS_PROYECTO.md (restricciones)
- [ ] LOG_ANALISIS.md (historial de sesiones para análisis)
- [ ] HISTORIAL.md (sesiones S1–S47, opcional para profundidad)

