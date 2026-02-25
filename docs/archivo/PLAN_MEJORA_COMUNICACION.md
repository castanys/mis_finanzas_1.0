# 🎯 Plan de Mejora de Comunicación con Haiku

**Propósito**: Optimizar la colaboración entre tú (usuario) y Haiku (desarrollador)

---

## Problema Identificado

**Antes**: 
- AGENTS.md era una copia de otro proyecto (mis_tickets)
- Documentación dispersa en 8+ archivos .md
- No había protocolo claro de cómo comunicarse con Haiku
- Ambigüedad sobre dónde hacer cambios y cómo verificarlos

**Ahora**:
- ✅ AGENTS.md consolidado y correcto para mis_finanzas_1.0
- ✅ Guía clara de comunicación con Haiku
- ✅ Resumen ejecutivo del estado del proyecto
- ✅ Protocolo PLAN/BUILD bien definido

---

## Documentos Creados

### 1. AGENTS.md (Consolidado)
**Archivo**: `AGENTS.md`
**Tamaño**: 503 líneas, 18KB
**Propósito**: Documento maestro para Haiku (BUILD mode)

**Contenido**:
- Criterio de éxito (verificación explícita)
- Protocolo PLAN/BUILD
- Descripción del proyecto + estado actual
- Regla #1: NUNCA parchear datos
- 3 reglas implementadas
- Arquitectura 5 capas (resumida)
- Comandos principales
- Estructura de archivos
- Estilo de código (reducido)
- Troubleshooting

**Uso**: Haiku lee esto al inicio de cada sesión

---

### 2. GUIA_COMUNICACION_HAIKU.md (NUEVO)
**Archivo**: `GUIA_COMUNICACION_HAIKU.md`
**Tamaño**: 350 líneas, 7.8KB
**Propósito**: Manual de flujo de trabajo contigo y Haiku

**Contenido**:
- Estructura efectiva de peticiones
- Cómo describir problemas para BUILD
- Cuándo escalar a PLAN
- Verificación de tareas (lo más importante)
- Información clave para Haiku
- Flujo típico de una tarea
- Formato de reporte final
- Errores frecuentes
- Casos de uso comunes
- Checklist de finalización

**Uso**: Léela antes de pedir cambios. Sirve como "contract" entre tú y Haiku.

---

### 3. RESUMEN_PROYECTO_2026.md (NUEVO)
**Archivo**: `RESUMEN_PROYECTO_2026.md`
**Tamaño**: 300 líneas, 7.3KB
**Propósito**: Visión general ejecutiva (no técnica)

**Contenido**:
- Métricas clave (15,912 tx, 98.5% cobertura, 100% accuracy)
- Arquitectura en diagrama
- 3 reglas activas explicadas
- Validación 3 meses
- Documentación disponible
- Próximos pasos opcionales
- Comandos día a día
- Orden de lectura para nuevos devs
- Reglas críticas (NUNCA/SIEMPRE)

**Uso**: Para tener una visión clara del estado sin leer detalles técnicos

---

## Recomendaciones de Uso

### Para ti (Usuario/Pablo):

#### ✅ Antes de cada sesión:
1. Revisar `RESUMEN_PROYECTO_2026.md` (5 min) - entender estado
2. Tener `GUIA_COMUNICACION_HAIKU.md` como referencia

#### ✅ Cuando pidas un cambio:
1. Describir **qué quieres** (objetivo claro)
2. Explicar **por qué** (contexto)
3. Mencionar **restricciones** (NUNCA parchear, etc.)
4. Pedir **verificación explícita** (query de comprobación)

**Ejemplo BUENO**:
```
Objetivo: Clasificar transacciones "RESTO" como Otros/Otros
Razón: Aparecen 5 veces en enero 2026 sin clasificar
Dónde: classifier/merchants.py Capa 2
Verificación: SELECT COUNT(*) FROM transacciones WHERE cat2='Otros'
```

**Ejemplo MALO**:
```
Mejora el clasificador
```

#### ✅ Cuando recibas respuesta de Haiku:
1. Verificar que el número final coincide con lo esperado
2. Si no coincide, pedir investigación
3. Confirmar que el cambio funciona para todos los casos

---

### Para Haiku (Desarrollador):

#### ✅ Al inicio de cualquier tarea:
1. Leer AGENTS.md (referencias cruzadas según sea necesario)
2. Entender la regla: **NUNCA parchear datos, SIEMPRE arreglar reglas**

#### ✅ Durante la implementación:
1. Modificar archivos en `classifier/`
2. Ejecutar `python3 reclassify_all.py`
3. Ejecutar query de verificación
4. Comparar número esperado vs actual

#### ✅ Al finalizar:
1. Usar formato de reporte: qué cambió, cuánto cambió, verificación
2. Si no coincide el número esperado: investigar y explicar
3. NO asumir que funcionó sin confirmar

---

## Protocolo PLAN/BUILD

### Cuándo BUILD (Haiku) hace el trabajo:

```
✅ Cambios en classifier/ (agregar regla)
✅ Cambios en tokens/merchants (keywords)
✅ Scripts de análisis (queries SQL)
✅ Debugging de parsers
✅ Correcciones puntuales
```

### Cuándo BUILD debe escalar a PLAN:

```
🚫 Nueva columna en tabla
🚫 Cambio de constraint o índice
🚫 Redefinición de identificadores
🚫 Cambio fundamental de lógica
🚫 2+ intentos fallidos en el mismo error
```

**Formato de escalada**:
```
[ESCALADO A PLAN REQUERIDO]
Problema: <qué necesito>
Evidencia: <logs/errors>
Hipótesis: <causa probable>
Bloqueo: <por qué BUILD no puede hacerlo>
Solicitud: <qué necesito de PLAN>
```

---

## Verificación: Lo Más Importante

**Regla de oro**: 

> **No asumir que funcionó. Verificar con números.**

### Patrón de Verificación

```python
# 1. ANTES
SELECT COUNT(*) FROM transacciones WHERE cat2='Otros'
# Resultado: 391

# 2. CAMBIO EN CLASSIFIER
# Editado: classifier/merchants.py
# Añadida regla: ("IVA", "Recibos", "Impuestos")

# 3. REPROCESAR
python3 reclassify_all.py
# Output: 15 transacciones reclasificadas

# 4. VERIFICAR DESPUÉS
SELECT COUNT(*) FROM transacciones WHERE cat2='Otros'
# Resultado: 376 ✅ (391 - 15 = 376)

# 5. VERIFICAR SIN REGRESIONES
SELECT COUNT(*) FROM transacciones WHERE cat1='Bizum'
# Resultado: 20 (sin cambios, esperado) ✅
```

---

## Matriz de Decisión: Cómo Comunicarte

| Situación | Acción | Documento |
|-----------|--------|-----------|
| "¿Qué comandos uso?" | Buscar en QUICKSTART.md | QUICKSTART.md |
| "¿Cuál es el estado?" | Leer visión general | RESUMEN_PROYECTO_2026.md |
| "Quiero pedir un cambio" | Usar estructura de petición | GUIA_COMUNICACION_HAIKU.md |
| "¿Cómo funciona el clasificador?" | Leer arquitectura 5 capas | AGENTS.md + SPEC_CLASIFICADOR_*.md |
| "¿Por qué NUNCA parchear?" | Leer principios | REGLAS_PROYECTO.md |
| "¿Qué reglas están activas?" | Leer detalles | REGLAS_IMPLEMENTADAS.md |
| "Tengo un error, ¿cómo lo arreglo?" | Ver troubleshooting | AGENTS.md |

---

## Mejoras Futuras (Fase 6)

1. **Dashboard web** (opcional)
   - Visualizar transacciones
   - Gráficos por categoría
   - Filtros interactivos

2. **Automatización**
   - Procesar CSVs automáticamente
   - Reportes mensuales automáticos
   - Alertas de gastos anormales

3. **Extensión de clasificación**
   - Google Places para merchants desconocidos
   - Reducir SIN_CLASIFICAR < 1%

---

## Checklist: Comunicación Efectiva

### Antes de pedir un cambio:
- [ ] Objetivo claro y medible
- [ ] Archivo específico a modificar (no "mejora el clasificador")
- [ ] Query de verificación lista
- [ ] Número esperado vs actual definido

### Cuando Haiku entrega:
- [ ] Se ejecutó la query de verificación
- [ ] El número coincide con lo esperado
- [ ] Explicación clara de qué cambió
- [ ] Confirmación sin regresiones

### Documentación actualizada:
- [ ] AGENTS.md refleja cambios (si son reglas nuevas)
- [ ] REGLAS_IMPLEMENTADAS.md actualizado (si es regla nueva)
- [ ] Test cases añadidos si es lógica nueva

---

## FAQ: Preguntas Frecuentes

**P: ¿Y si cambio de desarrollador (no Haiku)?**

R: Esta guía funciona para cualquier IA. El protocolo PLAN/BUILD es agnóstico del modelo. Solo asegúrate de:
1. Leer AGENTS.md al inicio
2. Usar el formato de escalada si es necesario
3. Verificar con numbers, no asumir

**P: ¿Qué hago si Haiku no reprocesa después de cambiar reglas?**

R: La verificación fallará (números no coincidirán). Pide explícitamente:
```
Reprocesa con: python3 reclassify_all.py
Verifica con: SELECT COUNT(*) FROM transacciones WHERE [criterio]
```

**P: ¿Puedo parchear la BD directamente?**

R: **NO.** Cada vez que reproceses, tus cambios se pierden. Siempre modifica reglas, reprocesa, verifica.

**P: ¿Qué pasa si aparece una regla nueva que nadie había visto?**

R: Añádela a `classifier/` (merchants.py o tokens.py), reprocesa, verifica. Si aparece en >5 transacciones, actualiza REGLAS_IMPLEMENTADAS.md.

---

## Resumen Ejecutivo

### El nuevo flujo es:

```
TÚ (Usuario)
    ↓
[Pides cambio con objetivo + verificación + restricciones]
    ↓
HAIKU (BUILD)
    ↓
[Modifica classifier/, reprocesa, verifica con query]
    ↓
TÚ (Validación)
    ↓
[Confirmas que número coincide]
    ↓
✅ TAREA COMPLETA
```

### Documentos maestros:

1. **AGENTS.md** → Haiku aprende aquí
2. **GUIA_COMUNICACION_HAIKU.md** → Tú usas esto para pedir cambios
3. **RESUMEN_PROYECTO_2026.md** → Visión general del estado

---

**Versión**: 1.0
**Fecha**: 2026-02-17
**Propósito**: Mejorar eficiencia y claridad en colaboración usuario-IA

🚀 **¡Listo para trabajar con esta nueva estructura!**
