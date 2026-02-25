# 🎯 INSTRUCCIONES: Implementar Sistema de Bitácora v3 en Este Proyecto

> **Para el agente IA**: Lee este archivo completo ANTES de hacer nada. Contiene las instrucciones exactas para crear el sistema de bitácora. Cuando termines, borra este archivo o muévelo a `docs/`.

---

## Qué es esto

Un sistema de 3 archivos que mantiene el estado del proyecto entre sesiones. Resuelve:
- Pérdida de contexto al cerrar/compactar
- Repetición de preguntas ya decididas
- Crecimiento descontrolado de tokens
- Falta de continuidad en proyectos largos

---

## PASO 1: Crear SESIONES.md

Crea `SESIONES.md` en la raíz del proyecto con esta estructura EXACTA.

**REGLAS DE FORMATO**:
- Máximo 150 líneas. Si excede → compactar (ver protocolo abajo).
- Sin prosa. Solo datos estructurados.
- Cada entrada de sesión: máximo 4 líneas.

```markdown
# SESIONES.md — [NOMBRE_PROYECTO]

**Última actualización**: [FECHA] — Sesión [N]

---

## 🔴 Decisiones Arquitectónicas (PERMANENTES — NO repetir)

Estas decisiones ya se tomaron. No volver a preguntar ni proponer alternativas.

| # | Decisión | Por qué | Sesión |
|---|----------|---------|--------|
| 1 | [Ej: SQLite, no PostgreSQL] | [Ej: Proyecto local, sin concurrencia] | S1 |

---

## 🟡 Estado Operativo

### Métricas Principales

| Métrica | Valor | Fuente |
|---------|-------|--------|
| [Métrica 1] | [Valor] | [Cómo verificar] |
| [Métrica 2] | [Valor] | [Cómo verificar] |

### Pendientes Activos

**ALTA**:
- [ ] [Tarea]: [Descripción corta]. Archivo: `[ruta]`. Estado: PENDIENTE
- [ ] [Tarea]: [Descripción corta]. Archivo: `[ruta]`. Estado: EN_PROGRESO

**MEDIA**:
- [ ] [Tarea]: [Descripción corta]. Estado: PENDIENTE

**BAJA**:
- [ ] [Tarea]: [Descripción corta]. Estado: PROPUESTA

---

## 🟢 Últimas Sesiones (máx 5 — las anteriores van a ARCHIVO)

### S[N] — [FECHA]
- **Hecho**: [qué se completó]
- **Decisión**: [si hubo alguna]
- **Próximo**: [qué sigue]

### S[N-1] — [FECHA]
- **Hecho**: [qué se completó]
- **Decisión**: [si hubo alguna]
- **Próximo**: [qué sigue]

---

## 📦 Resúmenes Compactados

### Sesiones S1–S[X] (compactado [FECHA])
[Resumen de 3-5 líneas: qué se construyó, decisiones clave, métricas inicio→fin]
```

### Notas para el agente:
- Rellena `[NOMBRE_PROYECTO]` con el nombre real.
- Rellena la tabla de métricas con las métricas reales del proyecto (ejecútalas si puedes).
- Deja las secciones de sesiones y resúmenes vacías si es la primera vez.
- Pon la fecha de hoy.

---

## PASO 2: Crear AGENTS.md

Crea `AGENTS.md` en la raíz del proyecto. Máximo 80 líneas.

```markdown
# AGENTS.md — Protocolo de Trabajo para [NOMBRE_PROYECTO]

---

## 🔴 REGLA CRÍTICA

Después de completar CUALQUIER bloque de trabajo:
1. Verifica el resultado (test, query, logs)
2. Actualiza `SESIONES.md` inmediatamente (métricas + pendientes + historial)
3. Si hubo decisión → añadir a tabla de Decisiones Arquitectónicas

**Excepción**: Si solo leíste o analizaste sin cambios, no actualices.

---

## ⛔ ANTES de proponer algo, verifica

1. ¿Está en "Decisiones Arquitectónicas" de SESIONES.md? → NO volver a preguntar. Citar la decisión.
2. ¿Se intentó antes y falló? → Buscar en historial por qué falló antes de reintentar.
3. ¿Ya existe en pendientes? → No duplicar. Actualizar estado si cambió.

---

## Protocolo de Trabajo

### Inicio de sesión
1. Leer `SESIONES.md` completo
2. Leer `REGLAS_PROYECTO.md`
3. Identificar pendiente prioritario o esperar instrucción

### Fin de bloque
1. Verificar resultado
2. Actualizar `SESIONES.md`:
   - Métrica en tabla → nuevo valor
   - Pendiente → marcar ✅ o actualizar estado
   - Añadir entrada en "Últimas Sesiones"
3. Si usas Git: `git add SESIONES.md && git commit -m "sesión [N]: [descripción]"`

### Escalado
Si un bloque falla 2+ veces → PARAR. Documentar en SESIONES.md como BLOQUEADO con evidencia. Pedir decisión al usuario.

---

## Protocolo de Compactación (cada 5 sesiones)

Cuando haya más de 5 entradas en "Últimas Sesiones":
1. Tomar las sesiones más antiguas (dejar solo las 5 más recientes)
2. Generar resumen de 3-5 líneas: decisiones, métricas inicio→fin, problemas resueltos
3. Mover resumen a sección "Resúmenes Compactados" de SESIONES.md
4. Borrar las entradas detalladas movidas
5. Commit: `compactar: sesiones [rango]`

---

## Límites de Tamaño (OBLIGATORIOS)

| Archivo | Máximo | Si excede |
|---------|--------|-----------|
| SESIONES.md | 150 líneas | Compactar historial |
| AGENTS.md | 80 líneas | Eliminar texto redundante |
| REGLAS_PROYECTO.md | 50 líneas | Solo reglas esenciales |

---

## Formato de Entrada de Sesión (RÍGIDO — no añadir campos)

```
### S[N] — [FECHA]
- **Hecho**: [qué]
- **Decisión**: [qué, o "ninguna"]
- **Próximo**: [qué]
```

Nada más. Sin narrativas, sin "descubrimientos", sin "notas extra".

---

## Comunicación

Toda comunicación con el usuario en **español**.

---

## Comandos Principales

```bash
# [Adaptar a tu proyecto — ejemplos:]
# python3 manage.py test          # Ejecutar tests
# python3 validate.py             # Verificar estado
# npm run build                   # Build
```
```

### Notas para el agente:
- Adapta la sección "Comandos Principales" a los comandos reales del proyecto.
- Si no hay comandos definidos aún, deja ejemplos comentados.

---

## PASO 3: Crear REGLAS_PROYECTO.md

Crea `REGLAS_PROYECTO.md` en la raíz del proyecto. Máximo 50 líneas.

```markdown
# REGLAS_PROYECTO.md — [NOMBRE_PROYECTO]

---

## Regla #1: Nunca parchear, siempre arreglar

❌ PROHIBIDO:
- Editar datos individuales en BD/CSV/JSON directamente
- Scripts "one-off" para parchear casos
- Modificar archivos de salida manualmente

✅ CORRECTO:
- Modificar lógica/reglas/configuración
- Reprocesar desde cero
- Verificar con test/query

### Flujo correcto
1. Identificar qué está mal
2. Analizar por qué
3. Arreglar regla/config/lógica
4. Reprocesar/rebuild
5. Validar resultado
6. Actualizar SESIONES.md

---

## Regla #2: Nunca inventar datos

- TODO dato debe tener fuente verificable
- Si necesitas crear excepciones → confirmar con usuario PRIMERO
- Si no estás seguro → preguntar, no asumir

---

## Regla #3: [ESPECÍFICA DEL PROYECTO]

[Añadir reglas específicas de este proyecto. Ejemplos:]
[- "Nunca modificar la API pública sin aprobación"]
[- "Tests deben pasar antes de marcar tarea como completada"]
[- "No instalar dependencias sin justificación"]

---

## Criterio de Éxito

Antes de dar una tarea por completada:
1. ¿Resultado coincide con objetivo del usuario?
2. ¿Tests/validaciones pasan?
3. ¿SESIONES.md actualizado?

Si alguna es NO → no está terminado.
```

### Notas para el agente:
- La Regla #3 es un placeholder. Sustituye con reglas reales del proyecto.
- Si no conoces reglas específicas, pregunta al usuario qué prohibiciones quiere.

---

## PASO 4: Verificar e inicializar

1. Confirma que los 3 archivos existen en la raíz:
   ```
   tu_proyecto/
   ├── SESIONES.md
   ├── AGENTS.md
   └── REGLAS_PROYECTO.md
   ```

2. Ejecuta las métricas del proyecto (tests, queries, lo que aplique) y rellena la tabla de métricas en SESIONES.md con valores REALES verificados.

3. Lista los pendientes reales del proyecto en SESIONES.md.

4. Si el proyecto usa Git:
   ```bash
   git add SESIONES.md AGENTS.md REGLAS_PROYECTO.md
   git commit -m "feat: sistema de bitácora v2"
   ```

5. Registra esta como Sesión 1 en el historial de SESIONES.md.

---

## PASO 5: Confirmar al usuario

Cuando termines, muestra al usuario:
- Los 3 archivos creados con sus rutas
- Las métricas iniciales que registraste
- Los pendientes que identificaste
- Pregunta si quiere añadir/modificar reglas específicas (Regla #3+)

---

## Referencia rápida: ¿Cuándo actualizar qué?

| Evento | SESIONES.md | AGENTS.md | REGLAS_PROYECTO.md |
|--------|-------------|-----------|-------------------|
| Completé un bloque de trabajo | ✅ Métricas + pendientes + historial | — | — |
| Se tomó una decisión arquitectónica | ✅ Tabla de decisiones | — | — |
| Cambió el protocolo de trabajo | — | ✅ Actualizar | — |
| Nueva prohibición/regla | — | — | ✅ Añadir regla |
| Hay más de 5 sesiones en historial | ✅ Compactar | — | — |
| SESIONES.md supera 150 líneas | ✅ Compactar agresivamente | — | — |

---

## Principios de diseño del sistema

1. **Jerarquía**: 🔴 Decisiones permanentes > 🟡 Estado operativo > 🟢 Sesión actual
2. **Brevedad**: Formato rígido, sin prosa. Cada entrada = máximo 4 líneas.
3. **Compactación**: Cada 5 sesiones se consolida. El archivo nunca crece sin control.
4. **Anti-repetición**: Antes de proponer algo, verificar decisiones cerradas.
5. **Verificación**: Nunca registrar una métrica sin haberla ejecutado/verificado.
6. **Token-budget**: Los 3 archivos juntos no deben superar ~280 líneas (~4KB).

---

**Versión**: v3  
**Última actualización**: 2026-02-22  
**Cambios desde v2**:
- Añadida Regla #4 (Verificación obligatoria con query SQL real)
- Añadida columna "Cómo verificar" en tabla de métricas de SESIONES.md
- Añadida sección "Taxonomía de Referencia" en AGENTS.md (21 Cat1 existentes)
